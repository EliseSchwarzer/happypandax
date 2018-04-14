from src.react_utils import (e,
                             createReactClass,
                             withRouter)
from src.ui import ui, ToggleIcon
from src.client import ItemType
from src.state import state
from src.views import itemview
from src import utils, item
from org.transcrypt.stubs.browser import __pragma__
__pragma__('alias', 'as_', 'as')

__pragma__('skip')
require = window = require = setInterval = setTimeout = setImmediate = None
clearImmediate = clearInterval = clearTimeout = this = document = None
JSON = Math = console = alert = requestAnimationFrame = None
js_undefined = location = localStorage = sessionStorage = None
__pragma__('noskip')

__pragma__("kwargs")


def item_view_menu(history,
                   on_item_change=None,
                   default_item=None,
                   on_sort_change=None,
                   default_sort=None,
                   on_sort_desc=None,
                   default_sort_desc=None,
                   on_search=None,
                   default_search=None,
                   on_filter_change=None,
                   default_filter=None,
                   on_toggle_config=None):
    return [e(ui.Menu.Item, e(item.ItemButtons,
                              history=history,
                              on_change=on_item_change,
                              value=default_item,
                              query=True,
                              )),
            e(ui.Menu.Menu,
                e(ui.Menu.Item,
                    e(withRouter(item.Search), size="small", fluid=True,
                      on_search=on_search,
                      query=True, search_query=default_search), className="fullwidth",),
                position="left",
                className="fullwidth"),
            e(ui.Menu.Item,
              e(ToggleIcon, icons=["sort content ascending", "sort content descending"],
                on_toggle=lambda a: all((
                    on_sort_desc(a),
                    utils.go_to(history, query={'sort_desc': int(a)}, push=False))),
                toggled=default_sort_desc,
                ),
              e(item.SortDropdown,
                history=history,
                on_change=on_sort_change, value=default_sort,
                item_type=default_item,
                query=True)),
            e(ui.Menu.Item,
              e(ui.Icon, js_name="delete" if default_filter else "filter",
                link=True if default_filter else False,
                onClick=js_undefined if not default_filter else lambda: all((
                    on_filter_change(None, 0),
                    utils.go_to(history, query={'filter_id': 0}, push=False))),
                ),
              e(item.FilterDropdown,
                history=history,
                on_change=on_filter_change, value=default_filter,
                query=True)),
            e(ui.Menu.Item, e(ui.Icon, js_name="options", size="large"), icon=True, onClick=on_toggle_config),
            ]


__pragma__("nokwargs")


def itemviewpage_update(p_p, p_s):
    if any((
        p_p.view_type != this.props.view_type,
        p_s.item_type != this.state.item_type,
        p_s.filter_id != this.state.filter_id,
        p_s.sort_idx != this.state.sort_idx,
    )):
        this.update_menu()


def itemviewpage_render():
    return e(itemview.ItemView,
             history=this.props.history,
             location=this.props.location,
             item_type=this.state.item_type,
             view_filter=this.props.view_type,
             search_query=this.state.search_query,
             filter_id=this.state.filter_id,
             search_options=this.state.search_options,
             sort_by=this.state.sort_idx,
             sort_desc=this.state.sort_desc,
             toggle_config=this.toggle_config,
             visible_config=this.state.visible_config,
             config_suffix="main"
             )


ItemViewPage = createReactClass({
    'displayName': 'ItemViewPage',

    'toggle_config': lambda a: this.setState({'visible_config': not this.state.visible_config}),

    'on_item_change': lambda e, d: all((this.setState({'item_type': d.value,
                                                       'sort_idx': utils.session_storage.get("sort_idx_{}".format(d.value), this.state.sort_idx)}),
                                        utils.session_storage.set("item_type", d.value),
                                        )),

    'on_sort_change': lambda e, d: all((this.setState({'sort_idx': d.value}),
                                        utils.session_storage.set("sort_idx_{}".format(this.state.item_type), d.value))),

    'toggle_sort_desc': lambda d: all((this.setState({'sort_desc': not this.state.sort_desc}),
                                       utils.session_storage.set("sort_desc", not this.state.sort_desc))),

    'on_filter_change': lambda e, d: all((this.setState({'filter_id': d.value}),
                                          utils.session_storage.set("filter_id", utils.either(d.value, 0)))),

    'on_search': lambda s, o: all((this.setState({'search_query': s if s else '', 'search_options': o}),
                                   utils.session_storage.set("search_query", s, True),
                                   utils.storage.set("search_options", o))),

    'update_menu': lambda: state.app.set_menu_contents(
        item_view_menu(
            this.props.history,
            on_item_change=this.on_item_change,
            on_sort_change=this.on_sort_change,
            on_sort_desc=this.toggle_sort_desc,
            on_filter_change=this.on_filter_change,
            default_item=this.state.item_type,
            default_sort=this.state.sort_idx,
            default_sort_desc=this.state.sort_desc,
            default_search=this.state.search_query,
            default_filter=this.state.filter_id,
            on_search=this.on_search,
            on_toggle_config=this.toggle_config,
        )),

    'componentWillMount': lambda: this.update_menu(),

    'componentDidUpdate': itemviewpage_update,

    'getInitialState': lambda: {'item_type': utils.session_storage.get("item_type", int(utils.get_query("item_type", ItemType.Gallery))),
                                'filter_id': int(utils.either(utils.get_query("filter_id", None), utils.session_storage.get("filter_id", 0))),
                                'sort_idx': utils.session_storage.get("sort_idx_{}".format(utils.session_storage.get("item_type", ItemType.Gallery)), int(utils.get_query("sort_idx", 0))),
                                'sort_desc': utils.session_storage.get("sort_desc", bool(utils.get_query("sort_desc", 0))),
                                'search_query': utils.session_storage.get("search_query", "", True),
                                'search_options': utils.storage.get("search_options", {}),
                                'visible_config': False,
                                },

    'render': itemviewpage_render
})
