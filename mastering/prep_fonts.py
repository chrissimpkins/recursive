import os
from fontParts.fontshell import RFont as Font
from designspaceProblems import DesignSpaceChecker
from fontTools.designspaceLib import DesignSpaceDocument

# A re-write of Varfont Prep (https://github.com/arrowtype/varfont-prep)
# for the commandline. This just does what is needed to get the Recursive
# Sources in line for making variable fonts.


report = {}


def removeGlyphs(font, names):
    for name in names:
        for layer in font.layers:
            if name in layer.keys():
                layer.removeGlyph(name)

    for glyph in font:
        if glyph.components:
            for component in glyph.components:
                if component.baseGlyph in names:
                    glyph.removeComponent(component)

    glyphOrder = font.glyphOrder
    for name in glyphOrder:
        if name in names:
            glyphOrder.remove(name)
    font.glyphOrder = glyphOrder

    for left, right in font.kerning.keys():
        if left in names or right in names:
            del font.kerning[(left, right)]


def copyFiles(designspacePath):
    import shutil
    import datetime

    ignore = shutil.ignore_patterns(".git", ".git*")

    ds = DesignSpaceDocument.fromfile(designspacePath)
    sources = [source.path for source in ds.sources]

    now = datetime.datetime.now()

    font = Font(sources[0])
    fn = font.info.familyName.replace(" ", "_").lower()
    font.close()

    fn += "-varfontprep-" + now.strftime("%Y_%m_%d-%H_%M_%S")
    directory, file = os.path.split(designspacePath)
    root = os.path.join(directory, fn)
    if os.path.exists(root):
        print("🛑  new folder path exists, stopping")
        raise ValueError
    newDesignspacePath = os.path.join(root, file)
    os.mkdir(root)

    shutil.copy(designspacePath, newDesignspacePath)

    paths = {}
    for fontPath in sources:
        f = os.path.split(fontPath)[1]
        newPath = os.path.join(root, f)
        paths[f] = newPath
        shutil.copytree(fontPath, newPath, ignore=ignore)

    ds = DesignSpaceDocument.fromfile(newDesignspacePath)
    for source in ds.sources:
        source.path = paths[os.path.split(source.path)[1]]
    ds.write(newDesignspacePath)

    return newDesignspacePath


def writeReport(path):
    seperator = "\n_________________________"

    final_report = [seperator, "Cleared guidelines in:"]
    if report["Clear Guidelines"]:
        for font, glyphs in report["Clear Guidelines"]:
            final_report.append(f"\t{font}")
            if glyphs:
                final_report.append(f"\t\tAnd these glyphs: {' '.join(glyphs)}")
    else:
        final_report.append("None! No guidelines to remove")

    final_report.append(seperator)
    final_report.append("Decomposed and removed these non-exporting glyphs:")
    if report["Non-exporting glyphs"]:
        for font, glyphs in report["Non-exporting glyphs"]:
            final_report.append(f"\t{font}")
            final_report.append(f"\t\t{', '.join(glyphs)}")
    else:
        final_report.append("None! No glyphs to remove")

    final_report.append(seperator)
    final_report.append("Removed these glyphs that were not common to all sources:")
    if report["Removed Glyphs"]:
        for font, glyphs in report["Removed Glyphs"]:
            final_report.append(f"\t{font}")
            final_report.append(f"\t\t{', '.join(glyphs)}")
    else:
        final_report.append("None! No glyphs to remove")

    final_report.append(seperator)
    final_report.append("Removed these non-compatible glyphs:")
    if report["Removed non-compatible glyphs"]:
        for glyph, reason in report["Removed non-compatible glyphs"]:
            final_report.append(f"\t{glyph} because:")
            final_report.append(f"\t\t{reason}")
    else:
        final_report.append("None! No glyphs to remove")

    final_report.append(seperator)
    final_report.append("Added blank kerning to these fonts:")
    if report["Added blank kerning"]:
        for font in report["Added blank kerning"]:
            final_report.append(f"\t{font}")
    else:
        final_report.append("None! All fonts had kerning.")

    final_report.append(seperator)
    final_report.append("Reported designspace problems from DesignspaceProblems:")
    if report["Designspace check"]:
        for problem in report["Designspace check"]:
            final_report.append(str(problem))
    else:
        final_report.append("No reported problems!")

    with open(path, "w") as writer:
        writer.write("\n".join(final_report))


def checkFamilyName(fonts):
    familyName = []
    for font in fonts:
        if font.info.familyName not in familyName:
            familyName.append(font.info.familyName)

    if len(familyName) != 1:
        print("🛑  source UFOs have different family names, stopping")
        print(f"{', '.join(familyName)}")
        return False
    else:
        return True


def clearGuides(font):
    local_report = report.get("Clear Guidelines", [])
    font.clearGuidelines()
    clearedGlyphs = []

    for glyph in font:
        if glyph.guidelines:
            glyph.clearGuidelines()
            clearedGlyphs.append(glyph.name)

    local_report.append((font.info.familyName + " " + font.info.styleName, clearedGlyphs))
    report["Clear Guidelines"] = local_report


def makeSourceFontsGlyphCompatible(fonts):
    local_report = report.get("Removed Glyphs", [])

    # Get a list of all glyphs in each font
    glyphSets = [font.keys() for font in fonts]

    # Use set intersection to get all common glyph from each list
    commonGlyphs = set.intersection(*map(set, glyphSets))

    for font in fonts:
        removed = []
        for name in font.keys():
            if name not in commonGlyphs:
                removed.append(name)
        if len(removed) != 0:
            removeGlyphs(font, removed)
            local_report.append((font.info.familyName + " " + font.info.styleName, removed))
    report["Removed Glyphs"] = local_report


def decomposeNonExportingGlyphs(fonts):
    local_report = report.get("Non-exporting glyphs", [])
    for font in fonts:
        non_exporting = []
        for glyph in font:
            if glyph.components:
                for component in glyph.components:
                    if component.baseGlyph in non_exporting:
                        component.decompose()
                    elif component.baseGlyph[0] == "_":
                        non_exporting.append(component.baseGlyph)
                        component.decompose()
        removeGlyphs(font, non_exporting)
        local_report.append((font.info.familyName + " " + font.info.styleName, non_exporting))
    report["Non-exporting glyphs"] = local_report


def sortGlyphOrder(fonts):
    for font in fonts:
        newGlyphOrder = font.naked().unicodeData.sortGlyphNames(font.glyphOrder, sortDescriptors=[dict(type="cannedDesign", ascending=True, allowPseudoUnicode=True)])
        font.glyphOrder = newGlyphOrder


def kerningCompatibility(fonts):
    local_report = report.get("Added blank kerning", [])

    for font in fonts:
        if len(font.kerning) == 0:
            font.kerning[("A", "A")] = 0
            local_report.append(font.info.familyName + " " + font.info.styleName)
    report["Added blank kerning"] = local_report


def makeCompatible(fonts):
    local_report = report.get("Removed non-compatible glyphs", [])
    nonCompatible = []

    for glyph in fonts[0]:
        for font in fonts[1:]:
            if glyph.name in font.keys():
                compatibility = glyph.isCompatible(font[glyph.name])
                if not compatibility[0]:
                    nonCompatible.append((glyph.name, str(compatibility)))
            else:
                nonCompatible.append((glyph.name, "Missing in font"))

    for font in fonts:
        removeGlyphs(font, [name for name, _ in nonCompatible])

    if nonCompatible != []:
        local_report.append(nonCompatible)
    report["Removed non-compatible glyphs"] = local_report


def prep(designspacePath):

    # Checking to see if there are any large issues with the designspace
    # file before doing anything
    dsc = DesignSpaceChecker(designspacePath)
    assert not dsc.hasStructuralProblems()

    ds = DesignSpaceDocument.fromfile(designspacePath)
    sources = [source.path for source in ds.sources]

    print("🏗  Opening sources")
    fonts = [Font(path) for path in sources]

    print("🏗  Checking family name")
    assert checkFamilyName(fonts)

    print("🏗  Removing non-exporting glyphs")
    decomposeNonExportingGlyphs(fonts)

    print("🏗  Clearing guides")
    for font in fonts:
        clearGuides(font)

    print("🏗  Removing glyphs that aren't in every font")
    makeSourceFontsGlyphCompatible(fonts)

    print("🏗  Removing non-compatible glyphs")
    makeCompatible(fonts)

    print("🏗  Making kerning compatible")
    kerningCompatibility(fonts)

    print("🏗  Sorting glyph order to be common")
    sortGlyphOrder(fonts)

    print("🏗  Closing and saving sources")
    for font in fonts:
        font.close(save=True)

    print("🏗  Checking full design space")
    dsc.checkEverything()
    report["Designspace check"] = dsc.problems

    print("🏗  Writing report")
    report_path = os.path.join(os.path.split(designspacePath)[0],
                               "varfontprep-report.txt")
    writeReport(report_path)

    print("✅ Done")


if __name__ == "__main__":
    import argparse
    description = """
    Prepares the sources of a designspace for building a variable font.

    By default it makes a copy of the designspace and sources, so your
    working files are never overwritten. This may be overridden.
    """
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("designspacePath",
                        help="The path to a designspace file")
    parser.add_argument("-o", "--overwrite", action="store_true",
                        help="Overwrite source files in place.")
    args = parser.parse_args()
    if not args.overwrite:
        print("🏗  Moving files")
        designspacePath = copyFiles(args.designspacePath)
    else:
        designspacePath = args.designspacePath
    prep(designspacePath)