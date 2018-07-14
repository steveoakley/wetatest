#!/usr/bin/python2.7
'''testing script for the compactimgseq.py command-line tool'''

import unittest
import os
import shutil
import tempfile
import subprocess


class CompactImgSeqTestCase(unittest.TestCase):
    '''Configurable test case for all invokations of compactimgseq'''

    def __init__(self, name, in_files, out_files=None, opts='',
                 expected_failure=False, expected_report=False,
                 folder_permissions=None):
        if out_files is None:
            out_files = in_files
        self.name = name
        self.in_files = in_files
        self.expected_out_files = out_files
        self.expected_failure = expected_failure
        self.expected_report = expected_report
        self.opts = opts
        self.folder_permissions = folder_permissions
        super(CompactImgSeqTestCase, self).__init__()

    def shortDescription(self):
        return self.name

    def setUp(self):
        # Create the temporary test folder
        temp_folder = tempfile.mkdtemp(dir=os.path.abspath('.'))
        self.folder_path = str(temp_folder)

        # Create the initial directory
        for filename in self.in_files:
            with open(os.path.join(self.folder_path, filename), 'w') as text_file:
                text_file.write('content')
        if self.folder_permissions:
            os.chmod(self.folder_path, self.folder_permissions)

    def tearDown(self):
        # Remove the temporary test folder
        if self.folder_permissions:
            os.chmod(self.folder_path, 0777)
        shutil.rmtree(self.folder_path)

    def runTest(self):
        '''execute the shell command and check for expected behaviour'''

        shell_cmd = './compactimgseq.py %s %s'%(self.opts, self.folder_path)
        try:
            output = subprocess.check_output(shell_cmd, shell=True)
            self.assertEqual(self.expected_report, len(output) > 0)
            out_files = os.listdir(self.folder_path)
            self.assertEqual(sorted(self.expected_out_files), sorted(out_files))

        except subprocess.CalledProcessError:
            # Nonzero return code.
            self.assertTrue(self.expected_failure)


def _run_tests():

    example_in = (
        'prodeng.11.jpg prodeng.11.png prodeng.27.jpg prodeng.32.jpg prodeng.32.png '
        'prodeng.33.png prodeng.47.png prodeng.55.jpg prodeng.55.png prodeng.56.jpg '
        'prodeng.68.jpg prodeng.72.png prodeng.94.png weta.17.jpg weta.22.jpg '
        'weta.37.jpg weta.55.jpg weta.96.jpg')
    example_out = (
        'prodeng.01.jpg prodeng.02.jpg prodeng.03.jpg prodeng.04.jpg prodeng.05.jpg '
        'prodeng.06.jpg prodeng.01.png prodeng.02.png prodeng.03.png prodeng.04.png '
        'prodeng.05.png prodeng.06.png prodeng.07.png weta.01.jpg weta.02.jpg '
        'weta.03.jpg weta.04.jpg weta.05.jpg')

    tests = (
        CompactImgSeqTestCase('typical',
                              ('seqA.01.tga', 'seqA.07.tga', 'seqB.05.pic', 'ni.txt'),
                              ('seqA.0003.tga', 'seqA.0005.tga',
                               'seqB.0003.pic', 'ni.txt'),
                              '--step 2 --start_frame 3 --padding 4'),
        CompactImgSeqTestCase('defaults',
                              ('seqA.03.tga', 'seqA.5.tga'),
                              ('seqA.01.tga', 'seqA.02.tga')),
        CompactImgSeqTestCase('empty', ()),
        CompactImgSeqTestCase('example', example_in.split(), example_out.split(),
                              '-r', expected_report=True),
        CompactImgSeqTestCase('invalid step', (), (), '--step 0', expected_failure=True),
        CompactImgSeqTestCase('invalid padding', (), (), '--padding -1',
                              expected_failure=True),
        CompactImgSeqTestCase('malformed seq', ('seqA.1.tga', 'seqA.01.tga'),
                              expected_failure=True),
        CompactImgSeqTestCase('all images', ('seqA.02.unk',), ('seqA.01.unk',),
                              '--assume_all_images'),
        CompactImgSeqTestCase('extension case', ('seqA.02.TGA',), ('seqA.01.TGA',)),
        CompactImgSeqTestCase('custom image format', ('seqA.02.unk',), ('seqA.01.unk',),
                              '--add_image_extension Unk'),
        CompactImgSeqTestCase('write not permitted', ('seqA.1.jpg',), ('seqA.01.jpg',),
                              folder_permissions=0444, expected_failure=True),
        CompactImgSeqTestCase('read not permitted', ('seqA.1.jpg',), ('seqA.01.jpg',),
                              folder_permissions=0222, expected_failure=True),
        CompactImgSeqTestCase('list file formats', (), (), '--list_image_extensions',
                              expected_report=True),
        CompactImgSeqTestCase('preview only', ('seqA.003.jpg',), None, '--preview',
                              expected_report=True)
    )

    suite = unittest.TestSuite(tests)
    unittest.TextTestRunner(verbosity=2).run(suite)


if __name__ == '__main__':
    _run_tests()
    