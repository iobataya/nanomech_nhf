import struct
from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest
from nanomech.gwyddion import export_gwyddion, STATIC, DYNAMIC
from nanomech.selection import select_points


def decode(blob):
    position=0
    def string():
        nonlocal position
        end=blob.index(b"\0",position)
        value=blob[position:end].decode()
        position=end+1
        return value
    def number(fmt):
        nonlocal position
        value=struct.unpack_from("<"+fmt,blob,position)[0]
        position+=struct.calcsize(fmt)
        return value
    def obj():
        nonlocal position
        name=string();size=number("I");end=position+size;result={}
        while position<end:
            key=string();kind=chr(blob[position]);position+=1
            if kind=="o":value=obj()
            elif kind=="s":value=string()
            elif kind=="i":value=number("i")
            elif kind=="d":value=number("d")
            elif kind=="D":value=[number("d") for _ in range(number("I"))]
            else:raise AssertionError(kind)
            result[key]=value
        assert position==end
        return result
    assert blob[:4]==b"GWYP"
    position=4
    result=obj()
    assert position==len(blob)
    return result


def test_binary_maps_and_geometry(tmp_path,monkeypatch):
    import nanomech.gwyddion as module
    monkeypatch.setattr(module,"load_nhf_file",lambda _:SimpleNamespace(attribute={
        "rect_axis_range":[3e-6,2e-6],"scanner_offset_x":1e-6,"scanner_offset_y":2e-6}))
    selection=select_points(3,2)
    static=pd.DataFrame({"point_index":range(6),**{key:[1,0,np.nan,4,5,6] for key,_,_ in STATIC}})
    dynamic=pd.DataFrame({"point_index":range(6),"frequency_index":0,**{key:[1,0,np.nan,4,5,6] for key,_,_ in DYNAMIC}})
    path=export_gwyddion(tmp_path/"result.gwy","sample.nhf",selection,static,dynamic,[100],{})
    content=decode(path.read_bytes())
    for i in range(8):
        field=content[f"/{i}/data"]
        assert (field["xres"],field["yres"])==(3,2)
        assert field["xreal"]==3e-6
        assert field["yreal"]==2e-6
        assert field["xoff"]==1e-6
        np.testing.assert_equal(field["data"],[6,5,4,1,0,np.nan])
        assert content[f"/{i}/mask"]["data"]==[0,0,0,0,0,1]
    assert content["/5/data/title"]=="E Store 100 Hz"
    assert content["/7/data"]["si_unit_z"]["unitstr"]==""


def test_single_pixel_size(tmp_path):
    from nanomech.gwy_export import savedata_gwy,GwySizeInfo
    path=tmp_path/"one.gwy"
    assert savedata_gwy(path,GwySizeInfo(1e-6,2e-6),[np.zeros((1,1))],["one"],["Pa"])
    field=decode(path.read_bytes())["/0/data"]
    assert field["xreal"]==1e-6
    assert field["yreal"]==2e-6


def test_export_failure_is_error(tmp_path,monkeypatch):
    import nanomech.gwyddion as module
    monkeypatch.setattr(module,"load_nhf_file",lambda _:SimpleNamespace(attribute={"rect_axis_range":[1.,1.]}))
    monkeypatch.setattr(module,"savedata_gwy",lambda *a,**kw:False)
    static=pd.DataFrame({"point_index":[0],**{key:[0.] for key,_,_ in STATIC}})
    dynamic=pd.DataFrame({"point_index":[0],"frequency_index":[0],**{key:[0.] for key,_,_ in DYNAMIC}})
    with pytest.raises(OSError,match="Failed to save"):
        export_gwyddion(tmp_path/"failed.gwy","sample.nhf",select_points(1,1),static,dynamic,[100],{})


@pytest.mark.parametrize("empty", [False, True])
def test_bulk_maps_match_rowwise_placement(tmp_path, monkeypatch, empty):
    import nanomech.gwyddion as module
    monkeypatch.setattr(module, "load_nhf_file", lambda _: SimpleNamespace(
        attribute={"rect_axis_range": [4e-6, 3e-6]}))
    selection = select_points(4, 3, crop_area="1,0:2,2")
    # Shuffled sparse rows, repeated indices, missing frequency, NaNs and zeros.
    static = pd.DataFrame({"point_index": [10, 1, 5, 1], **{
        key: np.array([7., 2., np.nan, 0.]) + k for k, (key, _, _) in enumerate(STATIC)}})
    dynamic = pd.DataFrame({"point_index": [5, 1, 10, 1, 5],
        "frequency_index": [1, 0, 1, 0, 0], **{
        key: np.array([np.nan, 2., 8., 0., 3.]) + k for k, (key, _, _) in enumerate(DYNAMIC)}})
    if empty:
        static, dynamic = static.iloc[:0], dynamic.iloc[:0]
    expected = np.full((14, 3, 4), np.nan)
    for channel, (column, _, _) in enumerate(STATIC):
        for row in static.itertuples():
            x, y = selection.xy(row.point_index)
            expected[channel, 2-y, x] = getattr(row, column)
    for kind, (column, _, _) in enumerate(DYNAMIC):
        for row in dynamic.itertuples():
            x, y = selection.xy(row.point_index)
            expected[5+kind*3+row.frequency_index, 2-y, x] = getattr(row, column)
    original_static, original_dynamic = static.copy(), dynamic.copy()
    path = export_gwyddion(tmp_path/"bulk.gwy", "sample.nhf", selection,
                          static, dynamic, [100, 200, 300], {})
    content = decode(path.read_bytes())
    for channel in range(14):
        np.testing.assert_equal(content[f"/{channel}/data"]["data"], expected[channel].ravel())
        np.testing.assert_equal(content[f"/{channel}/mask"]["data"], np.isnan(expected[channel]).ravel())
    assert content["/7/data/title"] == "E Store 300 Hz"
    assert content["/8/data/title"] == "E Loss 100 Hz"
    pd.testing.assert_frame_equal(static, original_static)
    pd.testing.assert_frame_equal(dynamic, original_dynamic)


@pytest.mark.parametrize("point_index", [-1, 12])
@pytest.mark.parametrize("target", ["static", "dynamic"])
def test_bulk_coordinates_reject_out_of_range(tmp_path, monkeypatch, point_index, target):
    import nanomech.gwyddion as module
    monkeypatch.setattr(module, "load_nhf_file", lambda _: SimpleNamespace(
        attribute={"rect_axis_range": [4e-6, 3e-6]}))
    static = pd.DataFrame({"point_index": [0], **{key: [0.] for key, _, _ in STATIC}})
    dynamic = pd.DataFrame({"point_index": [0], "frequency_index": [0],
                           **{key: [0.] for key, _, _ in DYNAMIC}})
    (static if target == "static" else dynamic).loc[0, "point_index"] = point_index
    with pytest.raises(ValueError, match="outside the map"):
        export_gwyddion(tmp_path/"invalid.gwy", "sample.nhf", select_points(4, 3),
                       static, dynamic, [100], {})
