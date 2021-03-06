#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import logging
import os
import subprocess
import sys
from typing import Optional, List, Text  # pylint: disable=unused-import

if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error
else:
    from pathlib2 import Path  # pylint: disable=import-error

from cmk.utils.log import VERBOSE
import cmk.utils.tty as tty
import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.exceptions import MKException

logger = logging.getLogger("cmk.base.localize")

LanguageName = str


# TODO: Inherit from MKGeneralException?
class LocalizeException(MKException):
    pass


domain = 'multisite'


def _locale_base():
    # type: () -> str
    return str(cmk.utils.paths.local_locale_dir)


def _pot_file():
    # type: () -> str
    local_pot_file = cmk.utils.paths.local_locale_dir / 'multisite.pot'
    if local_pot_file.exists():  # pylint: disable=no-member
        return str(local_pot_file)
    return _locale_base() + '/multisite.pot'


def _builtin_po_file(lang):
    # type: (str) -> Path
    return cmk.utils.paths.locale_dir / lang / 'LC_MESSAGES' / ('%s.po' % domain)


def _po_file(lang):
    # type: (str) -> str
    return _locale_base() + '/%s/LC_MESSAGES/%s.po' % (lang, domain)


def _mo_file(lang):
    # type: (str) -> str
    return _locale_base() + '/%s/LC_MESSAGES/%s.mo' % (lang, domain)


def _alias_file(lang):
    # type: (str) -> Path
    return Path(_locale_base(), lang, "alias")


def _localize_usage():
    # type: () -> None
    sys.stdout.write("""Usage: check_mk [-v] --localize COMMAND [ARGS]

Available commands are:
  update  LANG [ALIAS] ... Creates or updates a .po file for the given
                           language. The alias is an optional attribute
                           which will be used as display string in the
                           Multisite GUI.
  compile LANG         ... Compiles the .po file into a .mo file which can
                           be used by gettext.
  edit    LANG         ... Call update, open .po in editor and compile in one step

 The regular process for translating is:

 1.) Create/update the .po file for the given language
 2.) Edit the .po file
 3.) Compile the .po file to get a .mo file which can be used by gettext

 Locale files are located in: %s
""" % _locale_base())


def do_localize(args):
    # type: (List[str]) -> None
    if len(args) == 0:
        _localize_usage()
        sys.exit(1)

    command = args[0]

    try:
        lang = args[1]  # type: LanguageName
    except IndexError:
        raise LocalizeException('No language given')

    if not lang:
        raise LocalizeException('No language given')

    alias = None  # type: Optional[Text]
    if len(args) > 2:
        alias = args[2].decode("utf-8")

    commands = {
        "update": _localize_update,
        "compile": _localize_compile,
        "edit": _localize_edit,
    }
    f = commands.get(command)
    if f:
        _check_binaries()

        try:
            f(lang)
            _write_alias(lang, alias)
        except LocalizeException as e:
            logger.error("%s", e)
            sys.exit(1)
    else:
        allc = sorted(commands.keys())
        allc = [tty.bold + c + tty.normal for c in allc]
        logger.error("Invalid localize command. Allowed are: %s and %s.", ", ".join(allc[:-1]),
                     allc[-1])
        sys.exit(1)


def _write_alias(lang, alias):
    # type: (LanguageName, Optional[Text]) -> None
    if not alias:
        return

    alias_file_path = _alias_file(lang)
    if alias == '-' and alias_file_path.exists():
        alias_file_path.unlink()
        return

    with alias_file_path.open("w", encoding="utf-8") as f:
        f.write(alias)


def _check_binaries():
    # type: () -> None
    """Are the xgettext utils available?"""
    for b in ['xgettext', 'msgmerge', 'msgfmt']:
        if subprocess.call(['which', b], stdout=open(os.devnull, "wb")) != 0:
            raise LocalizeException('%s binary not found in PATH\n' % b)


def _get_languages():
    # type: () -> List[LanguageName]
    return [l for l in os.listdir(_locale_base()) if os.path.isdir(_locale_base() + '/' + l)]


def _localize_update_po(lang):
    # type: (LanguageName) -> None
    """Merge the current .pot file with a given .po file"""
    logger.log(VERBOSE, "Merging translations...")
    if subprocess.call(
        ['msgmerge', '-U', _po_file(lang), _pot_file()], stdout=open(os.devnull, "wb")) != 0:
        logger.error('Failed!')
    else:
        logger.info('Success! Output: %s', _po_file(lang))


def _localize_init_po(lang):
    # type: (LanguageName) -> None
    if subprocess.call(
        ['msginit', '-i',
         _pot_file(), '--no-translator', '-l', lang, '-o',
         _po_file(lang)],
            stdout=open(os.devnull, "wb")) != 0:
        logger.error('Failed!\n')


def _localize_sniff():
    # type: () -> None
    """Dig into the source code and generate a new .pot file"""
    logger.info('Sniffing source code...')

    paths = [
        cmk.utils.paths.default_config_dir,
        cmk.utils.paths.web_dir + "/app",
        cmk.utils.paths.lib_dir + "/python/cmk",
    ]
    if cmk.utils.paths.local_web_dir.exists():
        paths.append(str(cmk.utils.paths.local_web_dir))

    sniff_files = []
    for path in paths:
        for root, _dirs, files in os.walk(path):
            for f in files:
                if f.endswith(".py") or f.endswith(".mk"):
                    sniff_files.append(os.path.join(root, f))

    if subprocess.call([
            'xgettext', '--no-wrap', '--sort-output', '--force-po', '-L', 'Python',
            '--from-code=utf-8', '--omit-header', '-o',
            _pot_file()
    ] + sniff_files,
                       stdout=open(os.devnull, "wb")) != 0:
        logger.error('Failed!\n')
    else:
        header = r'''# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2010             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
msgid ""
msgstr ""
"Project-Id-Version: Check_MK Multisite translation 0.1\n"
"Report-Msgid-Bugs-To: checkmk-en@lists.mathias-kettner.de\n"
"POT-Creation-Date: 2011-05-13 09:42+0200\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: LANGUAGE <LL@li.org>\n"
"Language: LANGUAGE \n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"

'''

        f = open(_pot_file()).read()
        open(_pot_file(), 'w').write(header + f)
        logger.info('Success! Output: %s', _pot_file())


def _localize_edit(lang):
    # type: (LanguageName) -> None
    _localize_update(lang)

    editor = os.getenv("VISUAL", os.getenv("EDITOR", "/usr/bin/vi"))
    if not os.path.exists(editor):
        editor = 'vi'

    if subprocess.call([editor, _po_file(lang)]) == 0:
        _localize_compile(lang)
    else:
        logger.error("Aborted.")


def _localize_update(lang):
    # type: (LanguageName) -> None
    """Start translating in a new language"""
    po_file = _po_file(lang)
    _initialize_local_po_file(lang)
    _localize_sniff()

    if not os.path.exists(po_file):
        logger.info('Initializing .po file for language %s...', lang)
        _localize_init_po(lang)
    else:
        logger.info('Updating .po file for language %s...', lang)
        _localize_update_po(lang)


def _localize_compile(lang):
    # type: (LanguageName) -> None
    """Create a .mo file from the given .po file"""
    if lang not in _get_languages():
        raise LocalizeException('Invalid language given. Available: %s' %
                                ' '.join(_get_languages()))

    po_file = _po_file(lang)
    _initialize_local_po_file(lang)

    if not os.path.exists(po_file):
        raise LocalizeException('The .po file %s does not exist.' % po_file)

    if subprocess.call(['msgfmt', po_file, '-o', _mo_file(lang)]) != 0:
        logger.error('Failed!')
    else:
        logger.info('Success! Output: %s', _mo_file(lang))


def _initialize_local_po_file(lang):
    # type: (LanguageName) -> None
    """Initialize the file in the local hierarchy with the file in the default hierarchy if needed"""
    po_file = _po_file(lang)

    store.makedirs(po_file)

    builtin_po_file = _builtin_po_file(lang)
    if not os.path.exists(po_file) and builtin_po_file.exists():
        with builtin_po_file.open("r", encoding="utf-8") as source, \
             Path(po_file).open("w", encoding="utf-8") as dest:
            dest.write(source.read())
        logger.info('Initialize %s with the file in the default hierarchy', po_file)
