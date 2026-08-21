"""Tracked laptop listing sources."""

SITES = {
    "ebay": {
        "name": "eBay",
        "url": "https://www.ebay.com/sch/i.html?_nkw=laptop",
    },
    "newegg": {
        "name": "Newegg",
        "url": "https://www.newegg.com/p/pl?d=laptop",
    },
    "aliexpress": {
        "name": "AliExpress",
        "url": "https://www.aliexpress.com/w/wholesale-laptop.html",
    },
    "target": {
        "name": "Target",
        "url": "https://www.target.com/c/laptops-computers/-/N-5xtdh",
    },
    "flipkart": {
        "name": "Flipkart",
        "url": "https://www.flipkart.com/search?q=laptop",
    },
}

FIELD_DESCRIPTION = (
    "For each laptop listing, extract product title, price, stock or availability "
    "status, seller or brand name, rating if shown, product image URL, and listing URL."
)

