Use inaSpeechSegmenter to build a python cli tool, that separates music from noise, talking or silence to create music-segments. Use argparse for cli parsing. Also use pygame to build a simple ui with the following features:

## UI-Description:
- It should show a timeline and the mono-audio wave underneath it like shown in the picture
- In the timeline there should be transparent blocks, that marks a detected music segment.
- Each segment has a name, that is default initialized with `audioN` where N is the number of the segment.
- There should be a vertical line marking the current playing position

## Controls
### Playback
- Pressing Space plays the audio at the current position.
- Pressing Ctrl+h / Ctrl+l moves the current play position by 3 seconds to the right / left. Pressing shift at the same time leads to only 1 seconds change.

### Selecting segments
- Clicking on a segment marks this segment.
- Clicking outside of a segment and draging a rectangle marks all segments in that rectangle.

### Changing segments
- Clicking onto a segment and dragging moves this segment.
- Draging a side of a segment moves only this side of the segment.
- Double clicking on a segment lets me edit the name of the segment

### Create / delete segments
- Pressing d removes all selected segments
- Pressing n creates a new segment at the current position with name `audioN` (choose an N, that is not taken yet).

### View control
- Scrolling with control pressed zooms out or in the timeline, scrolling without control move the view window left / right
- The view should never follow the current playing position, but pressing f should move the view, so that the current playing position is on the left side of the screen (with a margin).
- Pressing h / l moves the view left / right by 3 seconds
- Pressing j / k moves the view to the next / prev segment and sets play position to the start position of that segment

### Other
- Pressing Ctrl+z undos the last operation.
- Pressing Ctrl+e creates a new directory and exports to files "output/<input-filename-without-ext>/<segment-name>" for all segments. If the directory "output/<input-filename-without-ext>" already exists, create a new name by appending "-X" where X is a number, that was not taken yet.
