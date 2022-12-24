import os
import pathlib
import shutil
import sys
import tarfile
import tempfile
from urllib.request import urlopen

import gdown
from lxml import etree

ISFDB_IMG_DIR = "/home/owner/rec_sys_app/recsys/static/recsys/images/isfdb/"
ISFDB_DOWNLOAD_PAGE = "https://isfdb.org/wiki/index.php/ISFDB_Downloads"
IMG_LINKS_XPATH = "//*[@id='Image_Backups']//parent::h3//following-sibling::ul[1]//descendant::a/@href"


with tempfile.TemporaryDirectory() as down_dir:
    os.chdir(down_dir)

    with urlopen(ISFDB_DOWNLOAD_PAGE) as response:
        body = response.read()

    tree = etree.HTML(body)
    links = tree.xpath(IMG_LINKS_XPATH)

    if not links:
        print("Download links not found.")
        sys.exit(1)

    for link in links:
        try:
            filename = gdown.download(link, fuzzy=True)
        except Exception as exp:
            raise Exception(f"Can't download {link}") from exp
        try:
            print(f"Extracting {filename}...")
            with tarfile.open(filename) as tf:
                tf.extractall()
                member = tf.members[0]
        except Exception as exp:
            raise Exception(f"Can't exctract {filename}") from exp
        try:
            print(f"Deleting {filename}...")
            os.remove(filename)
        except FileNotFoundError:
            pass
        images_dir = pathlib.PurePath(member.name).parent
        print("Copying extracted files to app image directory...")
        shutil.copytree(images_dir, ISFDB_IMG_DIR, dirs_exist_ok=True)
        print("Deleting extracted files...\n")
        shutil.rmtree(images_dir, ignore_errors=True)
print("SUCCESS")
