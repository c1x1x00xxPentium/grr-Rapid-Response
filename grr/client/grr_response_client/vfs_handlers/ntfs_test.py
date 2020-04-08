#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import stat

from absl import app

from grr_response_client import vfs
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib


# File references manually extracted from ntfs.img.
A_FILE_REF = 281474976710721
ADS_FILE_REF = 1125899906842697
ADS_ADS_TXT_FILE_REF = 562949953421386
NUMBERS_TXT_FILE_REF = 281474976710720
A_B1_C1_D_FILE_REF = 281474976710728


class NTFSTest(vfs_test_lib.VfsTestCase, test_lib.GRRBaseTest):

  def _GetNTFSPathSpec(self,
                       path,
                       inode=None,
                       path_options=None,
                       stream_name=None):
    # ntfs.img is an NTFS formatted filesystem containing:
    # -rwxrwxrwx 1 root root    4 Mar  4 15:00 ./a/b1/c1/d
    # -rwxrwxrwx 1 root root 3893 Mar  3 21:10 ./numbers.txt
    # drwxrwxrwx 1 root root    0 Apr  7 15:23 ./ads
    # -rwxrwxrwx 1 root root    5 Apr  7 15:19 ./ads/ads.txt
    # -rwxrwxrwx 1 root root    6 Apr  7 15:48 ./ads/ads.txt:one
    # -rwxrwxrwx 1 root root    7 Apr  7 15:48 ./ads/ads.txt:two

    ntfs_img_path = os.path.join(self.base_path, "ntfs.img")
    return rdf_paths.PathSpec(
        path=ntfs_img_path,
        pathtype=rdf_paths.PathSpec.PathType.OS,
        path_options=rdf_paths.PathSpec.Options.CASE_LITERAL,
        nested_path=rdf_paths.PathSpec(
            path=path,
            pathtype=rdf_paths.PathSpec.PathType.NTFS,
            inode=inode,
            path_options=path_options,
            stream_name=stream_name))

  def testNTFSNestedFile(self):
    pathspec = self._GetNTFSPathSpec("/a/b1/c1/d")
    fd = vfs.VFSOpen(pathspec)
    self.assertEqual(fd.Read(100), b"foo\n")
    result = fd.Stat()
    self.assertEqual(
        result.pathspec,
        self._GetNTFSPathSpec("/a/b1/c1/d", A_B1_C1_D_FILE_REF,
                              rdf_paths.PathSpec.Options.CASE_LITERAL))

  def testNTFSOpenByInode(self):
    pathspec = self._GetNTFSPathSpec("/a/b1/c1/d")
    fd = vfs.VFSOpen(pathspec)
    self.assertEqual(fd.Read(100), b"foo\n")

    self.assertTrue(fd.pathspec.last.inode)
    fd2 = vfs.VFSOpen(fd.pathspec)
    self.assertEqual(fd2.Read(100), b"foo\n")

    pathspec = self._GetNTFSPathSpec("/ignored", fd.pathspec.last.inode,
                                     rdf_paths.PathSpec.Options.CASE_LITERAL)
    fd3 = vfs.VFSOpen(pathspec)
    self.assertEqual(fd3.Read(100), b"foo\n")

  def testNTFSStat(self):
    pathspec = self._GetNTFSPathSpec("numbers.txt")

    fd = vfs.VFSOpen(pathspec)
    s = fd.Stat()
    self.assertEqual(
        s.pathspec,
        self._GetNTFSPathSpec("/numbers.txt", NUMBERS_TXT_FILE_REF,
                              rdf_paths.PathSpec.Options.CASE_LITERAL))
    self.assertEqual(str(s.st_atime), "2020-03-03 20:10:46")
    self.assertEqual(str(s.st_mtime), "2020-03-03 20:10:46")
    self.assertEqual(str(s.st_crtime), "2020-03-03 16:46:00")
    self.assertEqual(s.st_size, 3893)

  def testNTFSListNames(self):
    pathspec = self._GetNTFSPathSpec("/")
    fd = vfs.VFSOpen(pathspec)
    names = fd.ListNames()
    expected_names = [
        "$AttrDef", "$BadClus", "$Bitmap", "$Boot", "$Extend", "$LogFile",
        "$MFT", "$MFTMirr", "$Secure", "$UpCase", "$Volume", "a", "ads",
        "numbers.txt"
    ]
    self.assertSameElements(names, expected_names)

  def testNTFSListFiles(self):
    pathspec = self._GetNTFSPathSpec("/")
    fd = vfs.VFSOpen(pathspec)
    files = fd.ListFiles()
    files = [f for f in files if not f.pathspec.Basename().startswith("$")]
    files = list(files)
    files.sort(key=lambda x: x.pathspec.Basename())
    expected_files = [
        rdf_client_fs.StatEntry(
            pathspec=self._GetNTFSPathSpec(
                "/a",
                inode=A_FILE_REF,
                path_options=rdf_paths.PathSpec.Options.CASE_LITERAL),
            st_atime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                "2020-03-03 16:48:16"),
            st_crtime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                "2020-03-03 16:47:43"),
            st_mtime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                "2020-03-03 16:47:50"),
            st_mode=stat.S_IFDIR,
        ),
        rdf_client_fs.StatEntry(
            pathspec=self._GetNTFSPathSpec(
                "/ads",
                inode=ADS_FILE_REF,
                path_options=rdf_paths.PathSpec.Options.CASE_LITERAL),
            st_atime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                "2020-04-07 14:57:02"),
            st_crtime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                "2020-04-07 13:23:07"),
            st_mtime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                "2020-04-07 14:56:47"),
            st_mode=stat.S_IFDIR,
        ),
        rdf_client_fs.StatEntry(
            pathspec=self._GetNTFSPathSpec(
                "/numbers.txt",
                inode=NUMBERS_TXT_FILE_REF,
                path_options=rdf_paths.PathSpec.Options.CASE_LITERAL),
            st_atime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                "2020-03-03 20:10:46"),
            st_crtime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                "2020-03-03 16:46:00"),
            st_mtime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                "2020-03-03 20:10:46"),
            st_mode=stat.S_IFREG,
            st_size=3893,
        ),
    ]
    # print("XX", str(files).replace("\\n", "\n"))
    self.assertEqual(files, expected_files)

  def testNTFSListFiles_alternateDataStreams(self):
    pathspec = self._GetNTFSPathSpec("/ads")
    fd = vfs.VFSOpen(pathspec)
    files = fd.ListFiles()
    files = list(files)
    files.sort(key=lambda x: x.pathspec.Basename())
    expected_files = [
        rdf_client_fs.StatEntry(
            pathspec=self._GetNTFSPathSpec(
                "/ads/ads.txt",
                inode=ADS_ADS_TXT_FILE_REF,
                path_options=rdf_paths.PathSpec.Options.CASE_LITERAL),
            st_atime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                "2020-04-07 13:48:51"),
            st_crtime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                "2020-04-07 13:18:53"),
            st_mtime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                "2020-04-07 13:48:56"),
            st_mode=stat.S_IFREG,
            st_size=5,
        ),
        rdf_client_fs.StatEntry(
            pathspec=self._GetNTFSPathSpec(
                "/ads/ads.txt",
                inode=ADS_ADS_TXT_FILE_REF,
                path_options=rdf_paths.PathSpec.Options.CASE_LITERAL,
                stream_name="one"),
            st_atime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                "2020-04-07 13:48:51"),
            st_crtime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                "2020-04-07 13:18:53"),
            st_mtime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                "2020-04-07 13:48:56"),
            st_mode=stat.S_IFREG,
            st_size=6,
        ),
        rdf_client_fs.StatEntry(
            pathspec=self._GetNTFSPathSpec(
                "/ads/ads.txt",
                inode=ADS_ADS_TXT_FILE_REF,
                path_options=rdf_paths.PathSpec.Options.CASE_LITERAL,
                stream_name="two"),
            st_atime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                "2020-04-07 13:48:51"),
            st_crtime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                "2020-04-07 13:18:53"),
            st_mtime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                "2020-04-07 13:48:56"),
            st_mode=stat.S_IFREG,
            st_size=7,
        ),
    ]
    # print("XX", str(files).replace("\\n", "\n"))
    self.assertEqual(files, expected_files)

  def testNTFSOpen_alternateDataStreams(self):
    pathspec = self._GetNTFSPathSpec("/ads/ads.txt")
    fd = vfs.VFSOpen(pathspec)
    self.assertEqual(fd.Read(100), b"Foo.\n")

    pathspec = self._GetNTFSPathSpec("/ads/ads.txt", stream_name="one")
    fd = vfs.VFSOpen(pathspec)
    self.assertEqual(fd.Read(100), b"Bar..\n")

    pathspec = self._GetNTFSPathSpec("/ads/ads.txt", stream_name="ONE")
    fd = vfs.VFSOpen(pathspec)
    self.assertEqual(fd.Read(100), b"Bar..\n")

    with self.assertRaises(IOError):
      pathspec = self._GetNTFSPathSpec(
          "/ads/ads.txt",
          stream_name="ONE",
          path_options=rdf_paths.PathSpec.Options.CASE_LITERAL)
      vfs.VFSOpen(pathspec)

    pathspec = self._GetNTFSPathSpec("/ads/ads.txt", stream_name="two")
    fd = vfs.VFSOpen(pathspec)
    self.assertEqual(fd.Read(100), b"Baz...\n")

    pathspec = self._GetNTFSPathSpec("/ads/ads.txt", stream_name="TWO")
    fd = vfs.VFSOpen(pathspec)
    self.assertEqual(fd.Read(100), b"Baz...\n")

    with self.assertRaises(IOError):
      pathspec = self._GetNTFSPathSpec(
          "/ads/ads.txt",
          stream_name="TWO",
          path_options=rdf_paths.PathSpec.Options.CASE_LITERAL)
      vfs.VFSOpen(pathspec)

  def testNTFSStat_alternateDataStreams(self):
    pathspec = self._GetNTFSPathSpec("/ads/ads.txt", stream_name="ONE")

    fd = vfs.VFSOpen(pathspec)
    s = fd.Stat()
    self.assertEqual(
        s.pathspec,
        self._GetNTFSPathSpec(
            "/ads/ads.txt",
            ADS_ADS_TXT_FILE_REF,
            stream_name="one",
            path_options=rdf_paths.PathSpec.Options.CASE_LITERAL))
    self.assertEqual(str(s.st_atime), "2020-04-07 13:48:51")
    self.assertEqual(str(s.st_mtime), "2020-04-07 13:48:56")
    self.assertEqual(str(s.st_crtime), "2020-04-07 13:18:53")
    self.assertEqual(s.st_size, 6)

  def testNTFSOpenByInode_alternateDataStreams(self):
    pathspec = self._GetNTFSPathSpec(
        "/ignore", inode=ADS_ADS_TXT_FILE_REF, stream_name="ONE")
    fd = vfs.VFSOpen(pathspec)
    self.assertEqual(fd.Read(100), b"Bar..\n")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
