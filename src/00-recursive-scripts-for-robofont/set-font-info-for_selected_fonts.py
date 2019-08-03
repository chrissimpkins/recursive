from vanilla.dialogs import *

inputFonts = getFile(
    "select UFOs", allowsMultipleSelection=True, fileTypes=["ufo"])
    
prop = 'Sans'

for fontPath in inputFonts:
    font = OpenFont(fontPath, showInterface=False)

    # for other font info attributes, see
    # http://unifiedfontobject.org/versions/ufo3/fontinfo.plist/

    print(font.info.familyName + "\n " + font.info.styleName)
    
    # f.info.openTypeOS2VendorID = "ARRW"
    if prop in font.info.familyName:
        
        font.info.familyName = "Recursive"
    
        currentStyleName = font.info.styleName
        
        if currentStyleName.split(' ')[-1] == "Italic":   
            font.info.styleName = f"{prop} {currentStyleName.split(' ')[-3]} {currentStyleName.split(' ')[-2]} Slanted"
        else:
            font.info.styleName = f"{prop} {currentStyleName.split(' ')[-2]} {currentStyleName.split(' ')[-1]}"
    
        # font.info.copyright = "Copyright 2019 The Recursive Project Authors (github.com/thundernixon/recursive)"

    if "Gothic" in font.info.styleName:
        
        font.info.styleName = font.info.styleName.replace("Gothic", "Linear")

    print("→ " + font.info.familyName + "\n→ " + font.info.styleName)
    print("")

    font.save()
    font.close()
