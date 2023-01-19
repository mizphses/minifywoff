from fontTools import subset
from fontTools.ttLib import TTFont, woff2

def subsettor(ttffont, text="", filename=""):
    font = TTFont(ttffont)
    subsetter = subset.Subsetter()
    subsetter.populate(text=text)
    subsetter.subset(font)
    font.save(filename)
    woff2.compress(filename, filename)


def character_list(ttffont):
    font = ttffont
    charlist = []
    for i in font["cmap"].tables:
        for j in i.cmap.items():
            charlist.append(chr(j[0]))
    return charlist

def suggestion_charset(charlist):
    if '㋿' in charlist:
        return {"code": "aj17", "name":'Adobe Japan 1-7'}
    if '伵' in charlist:
        return {"code": "aj16", "name":'Adobe Japan 1-6'}
    elif '謁' in charlist:
        return {"code": "aj14", "name":'Adobe Japan 1-4'}
    elif '©' in charlist:
        return {"code": "jis2k", "name":'JIS第2水準+記号'}
    elif '弌' in charlist:
        return {"code": "jis2", "name":'JIS第2水準'}
    elif '亜' in charlist:
        return {"code": "jis1", "name":'JIS第1水準'}
    elif 'あ' in charlist:
        return {"code": "kana", "name":'かな'}
    else:
        return {"code": "other", "name":'その他'}
