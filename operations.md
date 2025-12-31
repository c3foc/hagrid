# Guide for Operations

This place is for writing down things you might want to know which are not
documented in the software itself or might not be self-explanatory.

## Dashboard text

The dashboard text in the store settings is now wrapped into a CSS container
that creates three columns. Each top-level HTML element in your entered HTML
will be its own column. This is a good example HTML:

```
<div> 
  <h2>Merch desk opening hours</h2>
  <ul>
    <li>Day 1: 13:00 - 24:00 <strong>Preorder pickup only</strong></li>
    <li>Day 2: 12:00 - 24:00</li>
    <li>Day 3: 12:00 - 22:00</li>
    <li>Day 4: closed</li>
  </ul>

  <p>Angel shirts are distributed by the Angel Shirt desk and/or Heaven, not FOC. Please check for annoucements in Engelsystem.</p>
</div>

%open_status%

<div>
  <h2>Contact</h2>
  <p>
    Check <a href="https://c3foc.net">c3foc.net</a> for updates on opening times and item availability. 
    For any questions, e.g. regarding the pickup of your preorder, come by the FOC desk or 
    call <a href="tel:1362">1FOC (1362 via DECT)</a>.
  </p>

  <p>Happy shopping!</p>
</div>
```

Note that a placeholder `%open_status%` exists to render the current open
status as an element. If you do not include it, it will not show up. It should
get its own column to look good.

Normal semantic HTML elements like `h2, h3, a, ul, li, p, b` etc. work great.


## Dashboard content

The dashboard only shows product groups. If you don't want to show a certain
product (yet), don't give it a group, or assign it to a group that is hidden
(checkbox in the product group admin).

The order of all items is:

* Product group, by `position`
* Product, by `position`
* Sizegroup, by `position`
* Size, by `position`

A product group can have a HTML description, like `<p>Only available on <b>DAY
3</b>.</p>`. It renders below the heading on the dashboard page.

## Product images

The product images on the dashboard are chosen at random from all gallery
images associated with a product. Add all your images as gallery images. If you
enter no name, then the Product + Sizegroup will be used for the title in the
gallery. That is usually fine.
 
The gallery images do not track item size anymore. You can't judge a size from
a picture anyway :)

There is a filtered gallery view for each product, which shows only images from
that product. It is linked on the "image" icon next to the product name in
mobile view, because there is so little space to show all images in the
availability list/dashboard itself.

## Open status

Make sure to create an order of entries that makes sense. Start with a "open"
state (usually "presale pickup"), then "closed", then "open", then "closed" and
so on. Do not leave the open state open forever, do not close it if it isn't
open, don't close before you open, and so on. The timing logic for stats might break otherwise :D


## Admin features


### Clear username

After the event, go to the adminpage for "Variation count events", select all
items, click "Select all XXX variation count events" on top, then choose from
the dropdown "Clear name" and press "Go". This removes all entered usernames,
which we promise (on the counting page) to clear after the event.


### Export count events

You can export a CSV for the count events from the admin. Like above, select
all items, then choose "Export CSV" in the dropdown instead. Of course you can
also filter that list first by some product or so, then export only that.

