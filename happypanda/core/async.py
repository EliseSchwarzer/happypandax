import sys
import gevent
import weakref
import collections
import threading
import functools

from happypanda.common import hlogger, utils, constants

log = hlogger.Logger(__name__)

class Greenlet(gevent.Greenlet):
    '''
    A subclass of gevent.Greenlet which adds additional members:
     - locals: a dict of variables that are local to the "spawn tree" of
       greenlets
     - spawner: a weak-reference back to the spawner of the
       greenlet
     - stacks: a record of the stack at which the greenlet was
       spawned, and ancestors
    '''

    def __init__(self, f, *a, **kw):
        super().__init__(f, *a, **kw)
        self._hp_inherit(self, weakref.proxy(gevent.getcurrent()), sys._getframe())

    @staticmethod
    def _hp_inherit(self, parent, frame):
        spawner = self.spawn_parent = parent
        if not hasattr(spawner, 'locals'):
            spawner.locals = {}
        self.locals = spawner.locals
        stack = []
        cur = frame
        while cur:
            stack.extend((cur.f_code, cur.f_lineno))
            cur = cur.f_back
        self.stacks = (tuple(stack),) + getattr(spawner, 'stacks', ())[:10]

class CPUThread():
    """
    Manages a single worker thread to dispatch cpu intensive tasks to.
    Signficantly less overhead than gevent.threadpool.ThreadPool() since it
    uses prompt notifications rather than polling.  The trade-off is that only
    one thread can be managed this way.
    Since there is only one thread, hub.loop.async() objects may be used
    instead of polling to handle inter-thread communication.
    """

    _thread = None

    def __init__(self):
        self.in_q = collections.deque()
        self.out_q = collections.deque()
        self.in_async = None
        self.out_async = gevent.get_hub().loop.async()
        self.out_q_has_data = gevent.event.Event()
        self.out_async.start(self.out_q_has_data.set)
        self.worker = threading.Thread(target=self._run)
        self.worker.daemon = True
        self.stopping = False
        self.results = {}
        # start running thread / greenlet after everything else is set up
        self.worker.start()
        self.notifier = gevent.spawn(self._notify)

    def _run(self):
        # in_cpubound_thread is sentinel to prevent double thread dispatch
        thread_ctx = threading.local()
        thread_ctx.in_cpubound_thread = True
        try:
            self.in_async = gevent.get_hub().loop.async()
            self.in_q_has_data = gevent.event.Event()
            self.in_async.start(self.in_q_has_data.set)
            while not self.stopping:
                if not self.in_q:
                    # wait for more work
                    self.in_q_has_data.clear()
                    self.in_q_has_data.wait()
                    continue
                # arbitrary non-preemptive service discipline can go here
                # FIFO for now, but we should experiment with others
                jobid, func, args, kwargs = self.in_q.popleft()
                try:
                    ret = self.results[jobid] = func(*args, **kwargs)
                except Exception as e:
                    log.exception("Exception raised in cpubound_thread:")
                    ret = self.results[jobid] = self._Caught(e)
                self.out_q.append(jobid)
                self.out_async.send()
        except:
            self._error()
            # this may always halt the server process

    def apply(self, func, args, kwargs):
        done = gevent.event.Event()
        self.in_q.append((done, func, args, kwargs))
        while not self.in_async:
            gevent.sleep(0.01)  # poll until worker thread has initialized
        self.in_async.send()
        done.wait()
        res = self.results[done]
        del self.results[done]
        if isinstance(res, self._Caught):
            raise res.err
        return res

    def _notify(self):
        try:
            while not self.stopping:
                if not self.out_q:
                    # wait for jobs to complete
                    self.out_q_has_data.clear()
                    self.out_q_has_data.wait()
                    continue
                self.out_q.popleft().set()
        except:
            self._error()

    class _Caught(object):
        def __init__(self, err):
            self.err = err

    def __repr__(self):
        cn = self.__class__.__name__
        return ("<%s@%s in_q:%s out_q:%s>" %
                (cn, id(self), len(self.in_q), len(self.out_q)))

    def _error(self):
        # TODO: something better, but this is darn useful for debugging
        log.exception()

class AsyncFuture:

    class NoValue:
        pass

    def __init__(self, cmd, f):
        self._cmd = cmd
        self._future = f
        self._value = self.NoValue

    def get(self, block=True, timeout=None):
        if not self._value == self.NoValue:
            return self._value
        if block:
            gevent.wait([self._future], timeout)
            self._value = self._future.get()
        else:
            self._value = self._future.get(block, timeout)
        return self._value

    def kill(self):
        if self._future:
            self._future.kill()

def defer(f=None, predicate=None):
    """
    Schedule a function to run in a cpu_bound thread, returns a AsyncFuture
    Optional predicate parameter to determine if the function should be dispatched
    """
    if f is None:
        def p_wrap(f):
            return defer(f, predicate)
        return p_wrap
    else:
        def f_wrap(f, *args, **kwargs):
            if CPUThread._thread is None:
                CPUThread._thread = CPUThread()
            return CPUThread._thread.apply(f, args, kwargs)

        def wrapper(*args, **kwargs):
            ctx = threading.local()
            a = AsyncFuture(None, None)
            if (predicate is not None and not predicate) or utils.in_cpubound_thread():
                v = f(*a, **kw)
                a._value = v
            else:
                g = Greenlet(f_wrap, f, *args, **kwargs)
                g.start()
                a._future = g
            return a
        return wrapper