#!/usr/bin/python2.7
'''A module for compacting image sequences.
'''

from __future__ import print_function
import logging as log
import tempfile
import os
import sys
import re

# These could be stored in an external config file:
DEFAULT_IMAGE_EXTENSIONS = ('bmp', 'dpx', 'exr', 'gif', 'hdr', 'jpeg', 'jpg', 'pbm',
                            'pgm', 'ppm', 'pcx', 'pic', 'png', 'psd', 'sgi', 'tga',
                            'tif', 'tiff', 'xbm')

DEFAULT_NEW_SEQ_START_FRAME = 1
DEFAULT_NEW_SEQ_STEP = 1
DEFAULT_NEW_SEQ_PADDING = 2


class FileError(Exception):
    '''Exception thrown when the filesystem does not permit an operation.'''
    pass

class SequenceError(Exception):
    '''Exception indicating that one of the sequences is poorly formed and cannot
    be reordered'''
    pass

class AbortError(Exception):
    '''Exception thrown when a renaming operation is been started but cannot be
    completed, and the image files have necessarily been left in an intermediate
    state.
    The temp_file_path member is the full path to the temporary folder which
    still contains isolated but un-renamed files.
    '''
    def __init__(self, msg, temp_file_path):
        self.temp_file_path = temp_file_path
        super(AbortError, self).__init__(msg)


def _find_sequences(filenames, image_extensions):
    '''Identify the sequences in a list of filenames.
    Returns a dictionary of sequences, of the form:
    { (seq_name, seq_ext): [(frame_number, image_filename), ...], ...}
    '''

    if image_extensions is None:
        image_extensions = DEFAULT_IMAGE_EXTENSIONS

    image_extensions = [ext.lower() for ext in image_extensions]

    seq_name_re = '.+'          # at least one character
    number_re = '-?[0-9]+'      # a possible negative, followed by at least one digit
    ext_re = '[^.]+'            # at least one non-period character
    image_filename_re = '^(%s)[.](%s)[.](%s)$'%(seq_name_re, number_re, ext_re)
    image_filename_re_obj = re.compile(image_filename_re)

    sequences = {}
    for filename in filenames:
        match_obj = image_filename_re_obj.match(filename)
        if match_obj:
            seq_name, image_number, ext = match_obj.groups()
            if image_extensions and ext.lower() not in image_extensions:
                continue

            seq_id = (seq_name, ext)
            images = sequences.get(seq_id)
            if images is None:
                images = []

            images.append((int(image_number), filename))
            sequences[seq_id] = images

    return sequences


def _generate_rename_ops(filenames, image_extensions, start_frame, step, padding):
    '''Generate a list of rename operations to perform on the supplied
    list of files.
    See the documentation of compact_image_sequences() for the usage of
    image_extensions, start_frame, step, padding.

    The return value is a list of tuples, of the form:
        (original_filename, new_filename)
    '''

    sequences = _find_sequences(filenames, image_extensions)

    rename_ops = []
    for seq_id, seq_images in sequences.items():
        seq_signature = '%s.#.%s'%seq_id
        seq_name, seq_ext = seq_id
        seq_images.sort(key=lambda v: v[0])

        log.info('Found sequence %s, %d images', seq_signature, len(seq_images))

        # Check this sequence for duplicate frames.
        # eg. seq.0001.tga and seg.1.tga belong to the same sequence, but share the same
        # frame number.  They would be renamed to the same destination file, and this
        # is a naming clash.  The sequence is considered to be poorly formed, with
        # inconsistent frame padding, and this should raise an exception.
        new_frame = start_frame
        prev_frame = None
        prev_filename = None
        for seq_img in seq_images:
            frame, old_filename = seq_img
            if prev_frame == frame:
                raise SequenceError('Sequence %s has multiple files which share '
                                    'the same frame number: %s and %s.'%
                                    (seq_signature, prev_filename, old_filename))

            new_filename = '%s.%0*d.%s'%(seq_name, padding, new_frame, seq_ext)
            rename_ops.append((old_filename, new_filename))
            new_frame += step
            prev_frame = frame
            prev_filename = old_filename

    return rename_ops


def _restore_isolated_files(isolated_files, src_folder, dst_folder):
    '''Restore files which have been isolated to their original location.
    In the unlikely event that this operation fails, we raise an
    AbortError, which contains a reference to the isolation folder in which
    some quarantined files remain.
    '''

    failed = False
    for filename in isolated_files:
        src_filepath = os.path.join(dst_folder, filename)
        dst_filepath = os.path.join(src_folder, filename)
        try:
            os.rename(src_filepath, dst_filepath)

        except OSError:
            failed = True

    if failed:
        raise AbortError('Failed to restore all isolated files from '
                         'temporary folder %s'%dst_folder, dst_folder)


def _isolate_files(files, src_folder, dst_folder):
    '''Move files to be renamed into a quarantine folder.

    A FileError is raised if the function can not be performed, but all
    files have been returned to their original location.

    An AbortError is raised if some files have been isolated, and can
    not be restored to their original location (in the event of an error).
    '''

    isolated_files = []
    try:
        for filename in files:
            src_filepath = os.path.join(src_folder, filename)
            dst_filepath = os.path.join(dst_folder, filename)
            os.rename(src_filepath, dst_filepath)
            isolated_files.append(filename)

    except OSError:
        log.debug('  Failed to isolate file %s', filename)
        _restore_isolated_files(isolated_files, src_folder, dst_folder)
        log.debug('Successfully restored isolated files')
        raise FileError('Unable to rename file %s'%filename)

    log.debug('Isolated all files successfully')


def _execute_rename_ops(rename_ops, src_folder, dst_folder):
    '''Move and rename the files accordingly to the supplied rename_ops.
    Each rename operation is a tuple (old_filename, new_filename).
    The file named old_filename in src_folder is moved to new_filename
    in dst_folder.
    '''

    #We have committed to executing all the rename operations, where possible.
    #In the unlikely event that a rename operation fails, we must raise an
    #AbortError, because the command has not execute completely.

    log.debug('Reordering files:')
    failed = False
    for rename_op in rename_ops:
        src_filename, dst_filename = rename_op
        src_filepath = os.path.join(src_folder, src_filename)
        dst_filepath = os.path.join(dst_folder, dst_filename)
        msg = '  %s ---> %s ... '%rename_op

        try:
            os.rename(src_filepath, dst_filepath)

        except OSError:
            failed = True

        msg += 'FAIL' if failed else 'ok'
        log.debug(msg)

    if failed:
        raise AbortError(
            'Not all files were successfully renamed and moved '
            'from the isolation folder at %s'%src_folder, src_folder)

    log.info('All %d files have been successfully reordered', len(rename_ops))


def print_default_image_extensions():
    '''Write the default image extensions to standard output, one format per line'''

    log.debug('Reporting recognised image file extensions')
    ext_str = ''
    for im_ext in DEFAULT_IMAGE_EXTENSIONS:
        ext_str += im_ext
        ext_str += '\n'

    print(ext_str)


def compact_image_sequences(
        folder_path, start_frame=DEFAULT_NEW_SEQ_START_FRAME,
        step=DEFAULT_NEW_SEQ_STEP, padding=DEFAULT_NEW_SEQ_PADDING,
        image_extensions=None, preview=False):
    '''Renumber image sequences in a folder according to a supplied numbering scheme.

    folder_path: an absolute path, or a path relative to the current directory,
        to a folder in which image sequences are to be renumbered.

    start_frame: the new frame number of the first image in each sequence
    step: the new frame spacing between each successive image in each sequence
    padding: the new minimum size of the frame number field in each sequence

    The files in an image sequence in the folder have the form:

        [seq_name].[frame_number].[extension]

    The sequence name can contain any characters permitted in a filename.
    The frame number is assumed to be integral (ie. contains no period)
    It is not assumed to be positive, however (it can contain a '-')
    The extension is assumed not to contain a period.  Extension is case
    sensitive - files with differing case in their extensions belong to
    difference sequences.

    image_extensions is a list of (case-insensitive) image format extensions.
    A file must have an extension in this list in order to be recognised as
    an image.  If it is the empty list, all files are assumed to be image files.
    If it is None, the default list is used.

    Returns a list of rename operations, each a tuple:
        (old_filename, new_filename).

    If preview is True, no changes are made to the directory - the rename operations
    are returned by the function, but are not executed.
    '''

    # argument validation
    if step <= 0:
        raise ValueError('step must be greater than zero')

    if padding < 0:
        raise ValueError('padding must not be negative')

    folder_path = os.path.abspath(folder_path)
    log.info('Compacting image sequences in %s', folder_path)
    log.debug('New starting frame = %d, step = %d', start_frame, step)

    if not os.path.isdir(folder_path):
        raise FileError('%s is not a folder'%folder_path)

    try:
        files = os.listdir(folder_path)

    except OSError:
        raise FileError('Cannot read the directory of %s'%folder_path)

    rename_ops = _generate_rename_ops(files, image_extensions,
                                      start_frame, step, padding)

    if preview:
        log.info('Not reordering sequences - preview only')

    else:
        try:
            temp_folder = tempfile.mkdtemp(dir=folder_path)

        except OSError:
            raise FileError('Unable to modify the contents of folder %s. '%folder_path)

        temp_folder_path = str(temp_folder)
        log.debug('Created quarantine folder at %s', temp_folder_path)

        try:
            src_files = [rename_op[0] for rename_op in rename_ops]
            _isolate_files(src_files, folder_path, temp_folder_path)
            _execute_rename_ops(rename_ops, temp_folder_path, folder_path)

        finally:
            # If the temporary folder is empty, we should remove it.
            files = os.listdir(temp_folder_path)
            if not files:
                os.rmdir(temp_folder_path)

            log.debug('Removed quarantine folder %s', temp_folder_path)

    return rename_ops


#########################################################################################


def _shell_cmd():

    import argparse

    #_prep_test_folder()

    tool_description = (
        'Renumber all image sequences in the specified folder into a '
        'compacted numbering scheme. An image sequence has the form: '
        '[sequence_name].[frame_number].[extension] '
        'The frame number is assumed to be an integer (not fractional), but it may be '
        'negative.  The extension must be one of the recognised file formats. '
        'Each unique image file sequence in the directory is renumbered according to '
        'an indicated uniform numbering scheme.  The start frame and  sequence frame '
        'step can be passed via the optional arguments.'
        )

    parser = argparse.ArgumentParser(description=tool_description)
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='write detailed progress information to stderr')
    parser.add_argument(
        '--report', '-r', action='store_true',
        help='write a report of the files that have been renamed. '
             'The report has one file per line: the original filename, followed by '
             'a \'>\' symbol, followed by the new filename.  It is output to standard '
             'output.')
    parser.add_argument(
        '--start_frame', '-sf', type=int, default=DEFAULT_NEW_SEQ_START_FRAME,
        help='set the start frame of each output image sequence.  Default is %d.'%
        DEFAULT_NEW_SEQ_START_FRAME)
    parser.add_argument(
        '--step', '-s', type=int, default=DEFAULT_NEW_SEQ_STEP,
        help='set the increment in frame number between successive files in each '
             'sequence.  By default, new frame numbers are consecutive')
    parser.add_argument(
        '--padding', '-p', type=int, default=DEFAULT_NEW_SEQ_PADDING,
        help='set the minimum with of the output frame number field for each renamed '
             'file.  The frame number is zero padded. '
             'Default is %d.'%DEFAULT_NEW_SEQ_PADDING)
    parser.add_argument(
        '--assume_all_images', '-aai', action='store_true',
        help='assume all filename extensions indicate valid image file formats')
    parser.add_argument(
        '--add_image_extension', '-aie', action='append',
        help='add an image file format extension to the known list of formats. '
             'The supplied extension is not case sensitive.  Multiple instances of '
             'the -aie flag can be passed.')
    parser.add_argument(
        '--list_image_extensions', '-lie', action='store_true',
        help='write the default list of image file extensions and exit')
    parser.add_argument(
        '--preview', '-pr', action='store_true',
        help='generate the renaming report, but do not proceed to renaming any files. '
             'The --report flag is ignored: the report is generated and sent to '
             'standard output instead of making any changes to the filesystem.')
    parser.add_argument(
        'folder_path', nargs='?', default=None,
        help='absolute path to the folder containing the files to be renumbered, or '
             'path relative to the current directory')

    args = parser.parse_args()

    logger_level = log.DEBUG if args.verbose else log.INFO
    log.basicConfig(level=logger_level, format='%(message)s')

    if args.list_image_extensions:
        print_default_image_extensions()
        exit()

    try:
        if not args.folder_path:
            parser.print_usage()
            raise ValueError('require a folder to process')

        # Force the generation of a renaming report if previewing.
        if args.preview:
            args.report = True

        if args.assume_all_images:
            im_exts = ()
        else:
            im_exts = DEFAULT_IMAGE_EXTENSIONS
            if args.add_image_extension:
                im_exts = im_exts + tuple(args.add_image_extension)

        kwargs = {key:args.__dict__[key] for key in [
            'start_frame', 'step', 'padding', 'preview']}
        rename_ops = compact_image_sequences(
            args.folder_path, image_extensions=im_exts, **kwargs)

        if args.report:
            log.info('Writing renaming report...')
            for rename_op in rename_ops:
                print('%s>%s'%rename_op)
            log.info('done')

    # Insulate the user from the python traceback.
    # The tool has a zero exit code on successful completion, and nonzero otherwise.
    except (AbortError, FileError, SequenceError, ValueError) as exc:
        log.error('error: %s', exc)
        sys.exit(1)


if __name__ == '__main__':
    _shell_cmd()
