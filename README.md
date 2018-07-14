# wetatest

compactimgseq
-------------

INTRODUCTION
------------
compactimgseq is a tool for reordering image sequences.

The package contains the following file:
    compactimgseq.py:       a python 2.7 module, also executable as a shell script.
    test_compactimgseq_.py: a python 2.7 script to test the operation of compactimgseq.py
    README.md:             this readme text file



The compactimgseq module defines the following functions:

    - compact_image_sequences
    - print_default_image_extensions

    Documentation of this module can be obtained through help() in a python interpreter.



The compactimgseq command line tool can be invoked in a shell.

    If the scripts are installed in a directory referenced by the PATH environment
    variable, the script can be invoked from anywhere:

        compactimgseq.py

    Otherwise, invoke it by including a path to it.  eg:

        ./compactimgseq.py

    Help on how to use the command line tool can be found by invoking it with the -h
    flag - it is built using the standard argparse module.

    For convenience, a softlink compactimgseq can reference compactimgseq.py, so that the
    python extension can be omitted during invokation.  The following shell command will
    create the link when run in the installation folder:

        ln -s compactimgseq.py compactimgseq



The command line tool can be tested using the test_compactimgseq.py script.
It is similarly invoked, and takes no arguments:

    ./test_compactimgseq.py
    
The test suite is implemented using the standard unittest module.



REQUIREMENTS
------------
The script requires that the python interpreter at /usr/bin/python2.7 exists.
(The VFX reference platform CY2018 recommends installation of python 2.7).
It will launch this interpreter from any Bourne-style shell.

The compactimgseq module depends only on standard python modules.



IMPLEMENTATION
--------------
This tool is intended to be used as part of a python script, a shell script (possibly
launched as a renderfarm job), or directly by a user on the shell command line.
As part of an automated script, it is important that the implementation be as robust
as possible, and either have no effect or fully complete, but avoid leaving the files
in an indeterminate state through partial completion.  It is also important that the
tool is able to write progress information to standard error with various levels of
verbosity, so that a renderfarm log will record the operation.  And vitally, the
shell script should generate correct exit codes so that a parent script or renderfarm
job dispatcher will halt.

We first analyse the directory to identify all the files which will need
renaming.  If this completes successfully, we then attempt to isolate all these files
into a temporary folder within the folder in which the files reside.  It is assumed that
if the folder permits directory changes, then it will likely permit the addition of a
temporary folder.  If we fail to isolate all files to the temporary folder, then we
attempt to return them, unchanged, to their original location, and fail gracefully with
no effect.
Once all files are successfully isolated, we can attempt to rename each of them while
moving them back into their original folder.

The shell script can generate a report which is output to standard output, and can
therefore be redirected to a file or piped to another script.  The report has a very
simple format, one renamed file per line, the old filename and the new filename
a single '>' character, so it can be simply parsed by another script, if necessary.
This is analogous to the operation of the main module function, which returns these
rename operations as a list of tuples, so that the calling script can be made aware of
what files have been modified, and how.

We can also execute the tool with a preview option, which will both force the
generation of a renaming report, and will also prevent the execution of any changes to
the filesystem, so that a user can preview the effect of the tool prior to executing it.

The tool is specifically for the reordering of image sequences, so non-image files are
be left unaffected in the folder.  The extension is assumed to identify the image file
format, and it is compared with a list of known image file formats.  The list can
be ignored, so that all files in the directory are assumed to be images, or it can be
added to when invoking the tool.



MAINTAINERS
-----------
Stephen Oakley - steve@steveoakleyvfx.com
