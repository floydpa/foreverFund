from paginate import Page

#---------------------------------------------------------------------------------------
# Modified pagination class to align with SQLAlchemy
#---------------------------------------------------------------------------------------

class MyPage(Page):
    """ See the documentation for Python's paginate """

    def __init__(self, collection, page=1, items_per_page=20, item_count=None,
                 wrapper_class=None, url_maker=None, **kwargs):

        self.pg = Page(collection, page, items_per_page, item_count, wrapper_class, url_maker, **kwargs)

        self.has_prev   = (self.pg.previous_page != None)
        self.has_next   = (self.pg.next_page != None)
        self.prev_num   = self.pg.previous_page
        self.next_num   = self.pg.next_page
        self.items      = self.pg.items
        self.page       = self.pg.page
        self.page_count = self.pg.page_count

        self.pages = []
        for p in range(self.pg.first_page, self.pg.last_page+1):
            self.pages.append(p)
        
    def iter_pages(self):
        return self.pages

    def __str__(self):
        return self.pg.__str__()

    def __repr__(self):
        return self.pg.__repr__()

