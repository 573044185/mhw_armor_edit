# coding: utf-8

from mhw_armor_edit.ftypes import StructFile, Struct


class MkitEntry(Struct):
    STRUCT_SIZE = 20
    result_item_id: "<I"
    research_points: "<I"
    melding_points: "<I"
    category: "<I"
    byte1: "<H"
    byte2: "<B"
    byte3: "<B"


class Mkit(StructFile):
    EntryFactory = MkitEntry
    MAGIC = 0x00B4
