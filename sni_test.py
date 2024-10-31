
_app_icon_size = 64

import os
import sys
import time

from PIL import Image
import io

import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gio
from gi.repository import GLib

class Bus:
    def __init__(self, conn, name, path):
        self.conn = conn
        self.name = name
        self.path = path

    def call_sync(self, interface, method, params, params_type, return_type):
        return self.conn.call_sync(
            self.name,
            self.path,
            interface,
            method,
            GLib.Variant(params_type, params),
            GLib.VariantType(return_type),
            Gio.DBusCallFlags.NONE,
            -1,
            None,
        )

    def get_menu_layout(self, *args):
        return self.call_sync(
            'com.canonical.dbusmenu',
            'GetLayout',
            args,
            '(iias)',
            '(u(ia{sv}av))',
        )
    
    
    def menu_event(self, *args):
        self.call_sync('com.canonical.dbusmenu', 'Event', args, '(isvu)', '()')
        
    def _user_activate(self):
        self.call_sync('org.kde.StatusNotifierItem', 'Activate', GLib.Variant("(ii)", (0, 0)), '(ii)', '()')
    
    def _user_secondary_activate(self):
        self.call_sync('org.kde.StatusNotifierItem', 'SecondaryActivate', GLib.Variant("(ii)", (0, 0)), '(ii)', '()')


conn = Gio.bus_get_sync(Gio.BusType.SESSION)

##############
from gi.repository import Gtk, GdkPixbuf ,Gdk, GObject

class MyButton(Gtk.Image):
    @GObject.Property
    def property_one(self):
        return self._property_one

    @property_one.setter
    def property_one(self, value):
        self._property_one = value

win = Gtk.Window()

def _exit(w):
    Gtk.main_quit()

win.connect('destroy', _exit)
win.set_size_request(500,500)
wbox = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 2)
win.add(wbox)


def _item_event(widget, event, args):
    if event.button == 1:
        name = args[0]
        path = args[1]
        menu = args[2]
        #
        try:
            bus = Bus(conn, name, path)
            bus._user_activate()
        except:
            pass
    elif event.button == 2:
        name = args[0]
        path = args[1]
        menu = args[2]
        name = args[0]
        path = args[1]
        menu = args[2]
        #
        try:
            bus = Bus(conn, name, path)
            bus._user_secondary_activate()
        except:
            pass
    elif event.button == 3:
        name = args[0]
        path = args[1]
        menu = args[2]
        _create_menu(name,menu,widget,event)

################## menu

_MENU = []
menu = None
_bus = None

def build_menu(conn, name, path):
    global _MENU
    del _MENU
    _MENU = []
    global _bus
    _bus = None
    _bus = Bus(conn, name, path)
    item = _bus.get_menu_layout(0, -1, [])[1]
    if item:
        _MENU = item[2]

####################

def _activate_item(widget, id):
    try:
        _bus.menu_event(id, 'clicked', GLib.Variant('s', ''), time.time())
    except:
        pass
        

def on_create_menu(menu, _data):
    id = _data[0]
    _dict = _data[1]
    #
    if 'toggle-type' in _dict:
        # 'checkmark'
        _toggle_type = _dict['toggle-type']
        _toggle_state = _dict['toggle-state']
        _label_name = _dict['label']
        if _toggle_type == 'checkmark':
            ckb = Gtk.CheckMenuItem.new_with_label(_label_name.replace("_",""))
            ckb.set_active(_toggle_state)
            ckb.connect('activate', _activate_item, id)
            menu.append(ckb)
    elif 'label' in _dict or 'accessible-desc' in _dict:
        _label_name = ""
        if 'accessible-desc' in _dict:
            if 'label' in _dict:
                _label_name = _dict['label'].replace("_","")
            else:
                return
        elif 'label' in _dict:
            _label_name = _dict['label'].replace("_","")
        #
        if 'icon-data' in _dict:
            _icon_data = _dict['icon-data']
            pb = None
            with Image.open(io.BytesIO(bytes(_icon_data))) as im:
                data = im.tobytes()
                w, h = im.size
                data = GLib.Bytes.new(data)
                pb = GdkPixbuf.Pixbuf.new_from_bytes(data, GdkPixbuf.Colorspace.RGB,
                        True, 8, w, h, w * 4)
            #
            img = Gtk.Image.new_from_pixbuf(pb)
            menu_item = Gtk.ImageMenuItem.new_with_label(_label_name)
            menu_item.set_image(img)
        elif 'icon-name' in _dict:
            _icon_name = _dict['icon-name']
            img = Gtk.Image.new_from_icon_name(_icon_name,Gtk.IconSize.MENU)
            menu_item = Gtk.ImageMenuItem.new_with_label(_label_name)
            menu_item.set_image(img)
        else:
            menu_item = Gtk.MenuItem.new_with_label(_label_name)
        _enabled = True
        if 'enabled' in _dict:
            _enabled = bool(_dict['enabled'])
        if _enabled:
            menu_item.connect('activate', _activate_item, id)
        else:
            menu_item.set_sensitive(_enabled)
        menu.append(menu_item)
        #
        if 'children-display' in _dict:
            _type = _dict['children-display']
            if _type == 'submenu':
                _submenu_data = _data[2]
                sub_menu = Gtk.Menu()
                for el in _submenu_data:
                    on_create_menu(sub_menu, el)
                menu_item.set_submenu(sub_menu)
    elif 'type' in _dict:
        _type = _dict['type']
        _enabled = True
        if 'enabled' in _dict:
            _enabled = bool(_dict['enabled'])
        if _type == 'separator':
            menu.append(Gtk.SeparatorMenuItem())

def _create_menu(name,_menu,widget,event):
    build_menu(conn, name, _menu)
    global menu
    #
    if menu:
        def _rec_remove(w):
            for child in menu.get_children():
                if isinstance(child, Gtk.Box):
                    _rec_remove(child)
                    child.destroy()
                    del child
                else:
                    w.remove(child)
        _rec_remove(menu)
        menu.destroy()
        del menu
        menu = None
    #
    menu = Gtk.Menu()
    #
    for _data in _MENU:
        on_create_menu(menu, _data)
    #
    menu.show_all()
    menu.popup_at_pointer()


def add_btn(_label, name=None, path=None, menu=None):
    btn_i = MyButton()
    btn = Gtk.EventBox()
    btn.add(btn_i)
    btn_i.set_tooltip_text(_label)
    btn_i.set_property('property_one',name)
    if menu != None:
        btn.connect('button-press-event', _item_event,[name,path,menu])
    wbox.add(btn)
    btn.show_all()

# remove button
def remove_btn(sender):
    for item1 in wbox.get_children():
        if isinstance(item1, Gtk.EventBox):
            item = item1.get_children()[0]
            if sender == item.get_property('property_one'):
                wbox.remove(item1)
                item1.destroy()
                break 

icon_theme = Gtk.IconTheme.get_default()

def _set_icon(icon_name, path):
    btn = None
    #
    for item1 in wbox.get_children():
        if isinstance(item1, Gtk.EventBox):
            item = item1.get_children()[0]
            if item.get_property('property_one') == path:
                btn = item
                break
    if btn != None:
        _pb = icon_theme.load_icon_for_scale(icon_name, _app_icon_size, 1, Gtk.IconLookupFlags.FORCE_SIZE)
        btn.set_from_pixbuf(_pb)


def _set_tooltip(_tooltip, path):
    btn = None
    #
    for item1 in wbox.get_children():
        if isinstance(item1, Gtk.EventBox):
            item = item1.get_children()[0]
            if item.get_property('property_one') == path:
                btn = item
                break
    #
    if btn != None:
        btn.set_tooltip_text(_tooltip)
    

# def _set_item_status(status, path):
    # pass


win.show_all()

###############

NODE_INFO = Gio.DBusNodeInfo.new_for_xml("""

<?xml version="1.0" encoding="UTF-8"?>
<node>
    <interface name="org.kde.StatusNotifierWatcher">
        <method name="RegisterStatusNotifierItem">
            <arg type="s" direction="in"/>
        </method>
        <property name="RegisteredStatusNotifierItems" type="as" access="read">
        </property>
        <property name="IsStatusNotifierHostRegistered" type="b" access="read">
        </property>
    </interface>
</node>""")

items = {}
old_items = {}


def _item_changed(sender, path):
    global items
    global old_items
    # 
    if len(items) > len(old_items):
        _path = sender+path
        _found = [_path, items[_path]]
        #
        old_items = items.copy()
        #
        if _found:
            if 'Status' in _found[1]:
                _status = _found[1]['Status']
                if _status == 'Passive':
                    return
            #
            _icon = _found[1]['IconName']
            #
            if 'ToolTip' in _found[1]:
                _label = _found[1]['ToolTip'][2]
            elif 'Title' in _found[1]:
                _label = _found[1]['Title']
            else:
                _label = ""
            #
            _name = _found[0].split("/")[0]
            _path =  "/"+"/".join(_found[0].split("/")[1:])
            if 'Menu' in _found[1]:
                _menu = _found[1]['Menu']
            else:
                _menu = None
            #
            add_btn(_label, _name, _path, _menu)
            # 
            _set_icon(_icon, _name)
        #
        return
    # 
    elif len(items) < len(old_items):
        _found = []
        for k,v in old_items.items():
            if items == {}:
                _found = [k,v]
                break
            else:
                if k not in items:
                    _found = [k,v]
                    break
        #
        if _found:
            # remove button
            sender = k.split("/")[0]
            remove_btn(sender)
            #
            old_items = items.copy()
            return
    #
    else:
        _path = sender+path
        if _path in items:
            item = items[_path]
            #
            old_item = None
            if _path in old_items:
                old_item = old_items[_path]
            if old_item:
                if item != old_item:
                    for key,v in item.items():
                        for kk,vv in old_item.items():
                            if key == kk:
                                if v != vv:
                                    if key == 'IconName':
                                        _icon = item['IconName']
                                        _set_icon(_icon, sender)
                                    elif key == 'ToolTip':
                                        _tooltip = item['ToolTip'][2]
                                        _set_tooltip(_tooltip, sender)
                                    elif key == 'Title':
                                        pass
                                    elif key == 'Status':
                                        _status = item['Status']
                                        if _status in ['Active', 'Attention']:
                                            # create a button
                                            if 'ToolTip' in item:
                                                _label = item['ToolTip'][2]
                                            elif 'Title' in item:
                                                _label = item['Title']
                                            else:
                                                _label = ""
                                            if 'Menu' in item:
                                                _menu = item['Menu']
                                            else:
                                                _menu = None
                                            #
                                            add_btn(_label, sender, path, _menu)
                                            # set the icon and tooltip
                                            _set_icon(_icon, sender)
                                        #
                                        else:
                                            remove_btn(sender)
                                    elif key == 'AttentionIconName':
                                        pass
                                    elif key == 'OverlayIconName':
                                        pass
                                    # elif key == 'IconThemePath':
                                        # pass
                                #
            old_items = items.copy()
            return
            
            
def render(sender, path):
    _item_changed(sender, path)

def get_item_data(conn, sender, path):
    def callback(conn, red, user_data=None):
        args = conn.call_finish(red)
        items[sender + path] = args[0]
        render(sender, path)

    conn.call(
        sender,
        path,
        'org.freedesktop.DBus.Properties',
        'GetAll',
        GLib.Variant('(s)', ['org.kde.StatusNotifierItem']),
        GLib.VariantType('(a{sv})'),
        Gio.DBusCallFlags.NONE,
        -1,
        None,
        callback,
        None,
    )


def on_call(
    conn, sender, path, interface, method, params, invocation, user_data=None
):
    props = {
        'RegisteredStatusNotifierItems': GLib.Variant('as', items.keys()),
        'IsStatusNotifierHostRegistered': GLib.Variant('b', True),
    }

    if method == 'Get' and params[1] in props:
        invocation.return_value(GLib.Variant('(v)', [props[params[1]]]))
        conn.flush()
    if method == 'GetAll':
        invocation.return_value(GLib.Variant('(a{sv})', [props]))
        conn.flush()
    elif method == 'RegisterStatusNotifierItem':
        if params[0].startswith('/'):
            path = params[0]
        else:
            path = '/StatusNotifierItem'
        get_item_data(conn, sender, path)
        invocation.return_value(None)
        conn.flush()


def on_signal(
    conn, sender, path, interface, signal, params, invocation, user_data=None
):
    if signal == 'NameOwnerChanged':
        if params[2] != '':
            return
        keys = [key for key in items if key.startswith(params[0] + '/')]
        if not keys:
            return
        for key in keys:
            del items[key]
        render(sender, path)
    elif sender + path in items:
        get_item_data(conn, sender, path)
    

def on_bus_acquired(conn, name, user_data=None):
    for interface in NODE_INFO.interfaces:
        if interface.name == name:
            conn.register_object('/StatusNotifierWatcher', interface, on_call)

    def signal_subscribe(interface, signal):
        conn.signal_subscribe(
            None,  # sender
            interface,
            signal,
            None,  # path
            None,
            Gio.DBusSignalFlags.NONE,
            on_signal,
            None,  # user_data
        )

    signal_subscribe('org.freedesktop.DBus', 'NameOwnerChanged')
    for signal in [
        'NewAttentionIcon',
        'NewIcon',
        'NewStatus',
        'NewTitle',
        'NewOverlayIcon',
        'NewToolTip',
    ]:
        signal_subscribe('org.kde.StatusNotifierItem', signal)


def on_name_lost(conn, name, user_data=None):
    sys.exit(
        f'Could not aquire name {name}. '
        f'Is some other service blocking it?'
    )
    


if __name__ == '__main__':
    owner_id = Gio.bus_own_name(
        Gio.BusType.SESSION,
        NODE_INFO.interfaces[0].name,
        Gio.BusNameOwnerFlags.NONE,
        on_bus_acquired,
        None,
        on_name_lost,
    )
    
    try:
        Gtk.main()
    finally:
        Gio.bus_unown_name(owner_id)

