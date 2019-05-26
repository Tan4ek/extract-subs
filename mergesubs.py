#!/usr/bin/env python3
# encoding: utf-8

import pysubs2
import chardet
from pysubs2 import SSAStyle, Color


def charset_detect(filename):
    with open(filename, 'rb') as fi:
        rawdata = fi.read()
    encoding = chardet.detect(rawdata)['encoding']
    return encoding


def merge(file1, file2, outfile):
    subs1 = pysubs2.load(file1, encoding=charset_detect(file1))
    subs2 = pysubs2.load(file2, encoding=charset_detect(file2))

    '''[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style:  Default,Arial, 16,     &H00FFFFFF,   &H00FFFFFF,     &H00000000,   &H00000000,-1,  0,     0,        0        ,100   ,100   ,0      ,0    ,1          ,3      ,0     ,2        ,10     ,10     ,10     ,0
Style:  Top ,Arial   ,16      ,&H00F9FFFF   ,&H00FFFFFF     ,&H00000000   ,&H00000000,-1  ,0     ,0        ,0        ,100   ,100   ,0      ,0    ,1          ,3      ,0     ,8        ,10     ,10     ,10     ,0
Style:  Mid ,Arial   ,16      ,&H0000FFFF   ,&H00FFFFFF     ,&H00000000   ,&H00000000,-1  ,0     ,0        ,0        ,100   ,100   ,0      ,0    ,1          ,3      ,0     ,5        ,10     ,10     ,10     ,0
Style:  Bot ,Arial   ,16      ,&H00F9FFF9   ,&H00FFFFFF     ,&H00000000   ,&H00000000,-1  ,0     ,0        ,0        ,100   ,100   ,0      ,0    ,1          ,3      ,0     ,2        ,10     ,10     ,10     ,0
'''
    style_top = SSAStyle()
    style_bot = SSAStyle()
    style_top.primarycolor = Color(249, 255, 255)
    style_bot.primarycolor = Color(249, 255, 249)
    style_bot.secondarycolor = Color(255, 255, 255)
    style_top.secondarycolor = Color(255, 255, 255)
    style_top.outline = 1.0
    style_bot.outline = 1.0
    style_top.shadow = 0.0
    style_bot.shadow = 0.0
    style_top.alignment = 8
    style_bot.alignment = 2
    # style_top.encoding # не знаю что значит, по умолчанию 1, в примере 0, оставлю 1
    subs2.styles['bot'] = style_bot
    subs2.styles['top'] = style_top

    for line in subs2:
        line.style = 'bot'

    for line in subs1:
        line.style = 'top'
        subs2.append(line)

    subs2.styles["Default"].fontsize = 14.0
    subs2.styles["Default"].shadow = 0.5
    subs2.styles["Default"].outline = 1.0
    subs2.save(outfile)
