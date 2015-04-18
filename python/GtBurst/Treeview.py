import Tkinter

_flatten = Tkinter._flatten

def _val_or_dict(options, func, *args):
    """Format options then call func with args and options and return
    the appropriate result.

    If no option is specified, a dict is returned. If a option is
    specified with the None value, the value for that option is returned.
    Otherwise, the function just sets the passed options and the caller
    shouldn't be expecting a return value anyway."""
    options = _format_optdict(options)
    res = func(*(args + options))

    if len(options) % 2: # option specified without a value, return its value
        return res

    return _dict_from_tcltuple(res)
    
def _dict_from_tcltuple(ttuple, cut_minus=True):
    """Break tuple in pairs, format it properly, then build the return
    dict. If cut_minus is True, the supposed '-' prefixing options will
    be removed.

    ttuple is expected to contain an even number of elements."""
    opt_start = 1 if cut_minus else 0

    retdict = {}
    it = iter(ttuple)
    for opt, val in zip(it, it):
        retdict[str(opt)[opt_start:]] = val

    return tclobjs_to_py(retdict)

def tclobjs_to_py(adict):
    """Returns adict with its values converted from Tcl objects to Python
    objects."""
    for opt, val in adict.iteritems():
        if val and hasattr(val, '__len__') and not isinstance(val, basestring):
            if getattr(val[0], 'typename', None) == 'StateSpec':
                val = _list_from_statespec(val)
            else:
                val = map(_convert_stringval, val)

        elif hasattr(val, 'typename'): # some other (single) Tcl object
            val = _convert_stringval(val)

        adict[opt] = val

    return adict

def _format_optdict(optdict, script=False, ignore=None):
    """Formats optdict to a tuple to pass it to tk.call.

    E.g. (script=False):
      {'foreground': 'blue', 'padding': [1, 2, 3, 4]} returns:
      ('-foreground', 'blue', '-padding', '1 2 3 4')"""
    format = "%s" if not script else "{%s}"

    opts = []
    for opt, value in optdict.iteritems():
        if ignore and opt in ignore:
            continue

        if isinstance(value, (list, tuple)):
            v = []
            for val in value:
                if isinstance(val, basestring):
                    v.append(unicode(val) if val else '{}')
                else:
                    v.append(str(val))

            # format v according to the script option, but also check for
            # space in any value in v in order to group them correctly
            value = format % ' '.join(
                ('{%s}' if ' ' in val else '%s') % val for val in v)

        if script and value == '':
            value = '{}' # empty string in Python is equivalent to {} in Tcl

        opts.append(("-%s" % opt, value))

    # Remember: _flatten skips over None
    return _flatten(opts)


class Treeview(Tkinter.Widget, Tkinter.XView, Tkinter.YView):
    """Ttk Treeview widget displays a hierarchical collection of items.

    Each item has a textual label, an optional image, and an optional list
    of data values. The data values are displayed in successive columns
    after the tree label."""

    def __init__(self, master=None, **kw):
        """Construct a Ttk Treeview with parent master.

        STANDARD OPTIONS

            class, cursor, style, takefocus, xscrollcommand,
            yscrollcommand

        WIDGET-SPECIFIC OPTIONS

            columns, displaycolumns, height, padding, selectmode, show

        ITEM OPTIONS

            text, image, values, open, tags

        TAG OPTIONS

            foreground, background, font, image
        """
        Tkinter.Widget.__init__(self, master, "ttk::treeview", kw)


    def bbox(self, item, column=None):
        """Returns the bounding box (relative to the treeview widget's
        window) of the specified item in the form x y width height.

        If column is specified, returns the bounding box of that cell.
        If the item is not visible (i.e., if it is a descendant of a
        closed item or is scrolled offscreen), returns an empty string."""
        return self.tk.call(self._w, "bbox", item, column)


    def get_children(self, item=None):
        """Returns a tuple of children belonging to item.

        If item is not specified, returns root children."""
        return self.tk.call(self._w, "children", item or '') or ()


    def set_children(self, item, *newchildren):
        """Replaces item's child with newchildren.

        Children present in item that are not present in newchildren
        are detached from tree. No items in newchildren may be an
        ancestor of item."""
        self.tk.call(self._w, "children", item, newchildren)


    def column(self, column, option=None, **kw):
        """Query or modify the options for the specified column.

        If kw is not given, returns a dict of the column option values. If
        option is specified then the value for that option is returned.
        Otherwise, sets the options to the corresponding values."""
        if option is not None:
            kw[option] = None
        return _val_or_dict(kw, self.tk.call, self._w, "column", column)


    def delete(self, *items):
        """Delete all specified items and all their descendants. The root
        item may not be deleted."""
        self.tk.call(self._w, "delete", items)


    def detach(self, *items):
        """Unlinks all of the specified items from the tree.

        The items and all of their descendants are still present, and may
        be reinserted at another point in the tree, but will not be
        displayed. The root item may not be detached."""
        self.tk.call(self._w, "detach", items)


    def exists(self, item):
        """Returns True if the specified item is present in the three,
        False otherwise."""
        return bool(self.tk.call(self._w, "exists", item))


    def focus(self, item=None):
        """If item is specified, sets the focus item to item. Otherwise,
        returns the current focus item, or '' if there is none."""
        return self.tk.call(self._w, "focus", item)


    def heading(self, column, option=None, **kw):
        """Query or modify the heading options for the specified column.

        If kw is not given, returns a dict of the heading option values. If
        option is specified then the value for that option is returned.
        Otherwise, sets the options to the corresponding values.

        Valid options/values are:
            text: text
                The text to display in the column heading
            image: image_name
                Specifies an image to display to the right of the column
                heading
            anchor: anchor
                Specifies how the heading text should be aligned. One of
                the standard Tk anchor values
            command: callback
                A callback to be invoked when the heading label is
                pressed.

        To configure the tree column heading, call this with column = "#0" """
        cmd = kw.get('command')
        if cmd and not isinstance(cmd, basestring):
            # callback not registered yet, do it now
            kw['command'] = self.master.register(cmd, self._substitute)

        if option is not None:
            kw[option] = None

        return _val_or_dict(kw, self.tk.call, self._w, 'heading', column)


    def identify(self, component, x, y):
        """Returns a description of the specified component under the
        point given by x and y, or the empty string if no such component
        is present at that position."""
        return self.tk.call(self._w, "identify", component, x, y)


    def identify_row(self, y):
        """Returns the item ID of the item at position y."""
        return self.identify("row", 0, y)


    def identify_column(self, x):
        """Returns the data column identifier of the cell at position x.

        The tree column has ID #0."""
        return self.identify("column", x, 0)


    def identify_region(self, x, y):
        """Returns one of:

        heading: Tree heading area.
        separator: Space between two columns headings;
        tree: The tree area.
        cell: A data cell.

        * Availability: Tk 8.6"""
        return self.identify("region", x, y)


    def identify_element(self, x, y):
        """Returns the element at position x, y.

        * Availability: Tk 8.6"""
        return self.identify("element", x, y)


    def index(self, item):
        """Returns the integer index of item within its parent's list
        of children."""
        return self.tk.call(self._w, "index", item)


    def insert(self, parent, index, iid=None, **kw):
        """Creates a new item and return the item identifier of the newly
        created item.

        parent is the item ID of the parent item, or the empty string
        to create a new top-level item. index is an integer, or the value
        end, specifying where in the list of parent's children to insert
        the new item. If index is less than or equal to zero, the new node
        is inserted at the beginning, if index is greater than or equal to
        the current number of children, it is inserted at the end. If iid
        is specified, it is used as the item identifier, iid must not
        already exist in the tree. Otherwise, a new unique identifier
        is generated."""
        opts = _format_optdict(kw)
        if iid:
            res = self.tk.call(self._w, "insert", parent, index,
                "-id", iid, *opts)
        else:
            res = self.tk.call(self._w, "insert", parent, index, *opts)

        return res


    def item(self, item, option=None, **kw):
        """Query or modify the options for the specified item.

        If no options are given, a dict with options/values for the item
        is returned. If option is specified then the value for that option
        is returned. Otherwise, sets the options to the corresponding
        values as given by kw."""
        if option is not None:
            kw[option] = None
        return _val_or_dict(kw, self.tk.call, self._w, "item", item)


    def move(self, item, parent, index):
        """Moves item to position index in parent's list of children.

        It is illegal to move an item under one of its descendants. If
        index is less than or equal to zero, item is moved to the
        beginning, if greater than or equal to the number of children,
        it is moved to the end. If item was detached it is reattached."""
        self.tk.call(self._w, "move", item, parent, index)

    reattach = move # A sensible method name for reattaching detached items


    def next(self, item):
        """Returns the identifier of item's next sibling, or '' if item
        is the last child of its parent."""
        return self.tk.call(self._w, "next", item)


    def parent(self, item):
        """Returns the ID of the parent of item, or '' if item is at the
        top level of the hierarchy."""
        return self.tk.call(self._w, "parent", item)


    def prev(self, item):
        """Returns the identifier of item's previous sibling, or '' if
        item is the first child of its parent."""
        return self.tk.call(self._w, "prev", item)


    def see(self, item):
        """Ensure that item is visible.

        Sets all of item's ancestors open option to True, and scrolls
        the widget if necessary so that item is within the visible
        portion of the tree."""
        self.tk.call(self._w, "see", item)


    def selection(self, selop=None, items=None):
        """If selop is not specified, returns selected items."""
        return self.tk.call(self._w, "selection", selop, items)


    def selection_set(self, items):
        """items becomes the new selection."""
        self.selection("set", items)


    def selection_add(self, items):
        """Add items to the selection."""
        self.selection("add", items)


    def selection_remove(self, items):
        """Remove items from the selection."""
        self.selection("remove", items)


    def selection_toggle(self, items):
        """Toggle the selection state of each item in items."""
        self.selection("toggle", items)


    def set(self, item, column=None, value=None):
        """With one argument, returns a dictionary of column/value pairs
        for the specified item. With two arguments, returns the current
        value of the specified column. With three arguments, sets the
        value of given column in given item to the specified value."""
        res = self.tk.call(self._w, "set", item, column, value)
        if column is None and value is None:
            return _dict_from_tcltuple(res, False)
        else:
            return res


    def tag_bind(self, tagname, sequence=None, callback=None):
        """Bind a callback for the given event sequence to the tag tagname.
        When an event is delivered to an item, the callbacks for each
        of the item's tags option are called."""
        self._bind((self._w, "tag", "bind", tagname), sequence, callback, add=0)


    def tag_configure(self, tagname, option=None, **kw):
        """Query or modify the options for the specified tagname.

        If kw is not given, returns a dict of the option settings for tagname.
        If option is specified, returns the value for that option for the
        specified tagname. Otherwise, sets the options to the corresponding
        values for the given tagname."""
        if option is not None:
            kw[option] = None
        return _val_or_dict(kw, self.tk.call, self._w, "tag", "configure",
            tagname)


    def tag_has(self, tagname, item=None):
        """If item is specified, returns 1 or 0 depending on whether the
        specified item has the given tagname. Otherwise, returns a list of
        all items which have the specified tag.

        * Availability: Tk 8.6"""
        return self.tk.call(self._w, "tag", "has", tagname, item)

