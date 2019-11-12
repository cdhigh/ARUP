# Brief Introduction
ARUP - Another bulk Rename Utility with embedded Python interpreter<br>
Arup is a another bulk rename utility, the point special is that it does not provide any renaming options.<br>
Only use python scripts as renaming rules.<br>
For this reason, this tool is for programmers or python-amateurs only.<br>
![Main dialog](https://raw.githubusercontent.com/cdhigh/ARUP/master/res/screenshots1.png)
![traceback for debug](https://raw.githubusercontent.com/cdhigh/ARUP/master/res/screenshots2.png)

## The features:
* Has built-in python interpreter, execute a python snippet to generate a desired new filename.
* Preview the renaming result before actually renaming.
* Can undo last renamed result.
* Add the code snippets you wrote to the library for reuse later.
* Sort files according to certain rules (Can also manually adjust the order).
* Filter files according to Unix filename pattern matching rules (\*.\*, a\*.mp3, ...).
* Choose to ignore certain files.

# Development & Deployment
  The utility is developed using Python3 / PyQt5 / peewee.<br>
  Be careful to keep your own snippets database file 'data/snippets.db' during the upgrade.<br>
  [github repository](https://github.com/cdhigh/ARUP)

# Python script
  ARUP execute a python function and use the result for renaming.<br>
  The signature of user function is **`def rename(arg)`**.<br>
    * **argument**: 'arg' is a dictionary that can access elements using attributes.<br>
    * **return**: This function will be called for each file to rename. return the desired new filename! return an empty string to skip renaming the file.<br>

  The dictionary `arg` has elements:<br>
  * **totalNum**: integer, total files number in list.<br>
  * **index**: integer, index of current file to rename, from 0.<br>
  * **fileName**: string, file name with extension.<br>
  * **dirName**: string, directory name of current file.<br>
  * **fullPathName**:  full filename, including path, file name with extension.<br>
  * **tag()**: function, **ONLY for music file**, you can execute `arg.tag()` to obtain tag object for current music archive.<br>    
    The tag object has the following attrbutes:<br>
      * tag.album         &emsp;# album as string<br>
      * tag.albumartist   &emsp;# album artist as string<br>
      * tag.artist        &emsp;# artist name as string<br>
      * tag.audio_offset  &emsp;# number of bytes before audio data begins<br>
      * tag.bitrate       &emsp;# bitrate in kBits/s<br>
      * tag.comment       &emsp;# file comment as string<br>
      * tag.composer      &emsp;# composer as string<br>
      * tag.disc          &emsp;# disc number<br>
      * tag.disc_total    &emsp;# the total number of discs<br>
      * tag.duration      &emsp;# duration of the song in seconds<br>
      * tag.filesize      &emsp;# file size in bytes<br>
      * tag.genre         &emsp;# genre as string<br>
      * tag.samplerate    &emsp;# samples per second<br>
      * tag.title         &emsp;# title of the song<br>
      * tag.track         &emsp;# track number as string<br>
      * tag.track_total   &emsp;# total number of tracks as string<br>
      * tag.year          &emsp;# year or data as string<br>

# License
   ARUP is Licensed under the [AGPLv3](http://www.gnu.org/licenses/agpl-3.0.html) license.
