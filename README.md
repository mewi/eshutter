# eshutter

## Installation

Copy the file "shutter.py" into your local plug-in directory.

You can find this folder in the settings under:

File -> Settings -> Folders -> Plugins

You will now have an additional option in the "Filters" drop-down menu, called "Eshutter".

## Usage

Select a region in the image that is covering a single band from top to bottom on a white or gray background.
Now select the "Capture" operation in the "Eshutter" menu.

When you subsequently select the "Fix" option the filter will try to remove the banding.
It first opens a dialog box with the following options:

- correct intensity: when selected the intensity will be corrected as well to follow a linear evolution between top and bottom
- correction width: 
    + selection: only correct the selected area
    + full: correct the full horizontal band from the left to the right image border
- soft edges: use soft edges at the top and bottom of the selection to harsh discontinuities

It is obviously possible to "sample" first by selecting a limited-width area with a clean white or gray background, and subsequently widen the selection or selecting a another band at a different height in the image before "fixing".

## Issues

Known issues (that can, should, and will someday be fixed):

- the plug-in is not very fast because it's using single-pixel operations rather tiles.
- the correction assumes that the band is perfectly horizontal and has a uniform color pattern across it's entire width.
- the plugin only support RGB color images, no alpha channel yet.
- the collected data by the "Capture" operation is saved in a file in "/tmp", which works on OSX and Linux, but probably not on Windows.

We warmly welcome all bug fixes, feature additions, comments, etc.
