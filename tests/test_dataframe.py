#coding: utf-8

import importlib
import datetime

from pytdx.util.pandas_adapter import DataFrame, concat, to_datetime


def _to_list(col):
    if hasattr(col, "tolist"):
        return col.tolist()
    return list(col)


def sample_data():
    return [
        {"code": "000001", "open": 10, "close": 12, "date": "20200101"},
        {"code": "000002", "open": 20, "close": 18, "date": "2020-01-02"},
        {"code": "000003", "open": 15, "close": 15, "date": "2020-01-03"},
    ]


def test_create_and_properties():
    df = DataFrame(data=sample_data())
    assert df.shape[0] == 3
    assert len(df) == 3
    assert "code" in df.columns


def test_column_access_and_slice():
    df = DataFrame(data=sample_data())
    codes = df["code"]
    assert _to_list(codes)[0] == "000001"

    sub = df[["code", "close"]]
    assert len(sub) == 3

    first_two = df[:2]
    assert len(first_two) == 2


def test_index_tuple_and_loc_equivalent():
    df = DataFrame(data=sample_data())
    HAS_PANDAS = importlib.util.find_spec("pandas") is not None
    if not HAS_PANDAS:
        vals = df[(slice(0, 2), "close")]
        assert _to_list(vals) == [12, 18]
    else:
        vals = _to_list(df.loc[0:1, "close"]) if hasattr(df, "loc") else _to_list(df["close"])[:2]
        assert vals == [12, 18]


def test_assign_filter_and_sort():
    df = DataFrame(data=sample_data())
    df2 = df.assign(spread=lambda r: r["close"] - r["open"])
    spreads = _to_list(df2["spread"]) if "spread" in getattr(df2, "columns", []) else _to_list(df2["spread"])
    assert spreads == [2, -2, 0]
    assert 'spread' in df2.columns
    assert 'spread' not in df.columns

    df2 = df.assign(price=lambda r: r["close"])
    assert _to_list(df2["price"]) == [12, 18, 15]
    assert 'price' in df2.columns
    assert 'price' not in df.columns

    df2 = df.assign(price=lambda r: r["open"] - 1)
    assert _to_list(df2["price"]) == [9, 19, 14]
    assert 'price' in df2.columns
    assert 'price' not in df.columns

    sorted_df = df.sort_values("open", ascending=False)
    assert _to_list(sorted_df["open"]) == [20, 15, 10]

def test_rename_column():
    df = DataFrame(data=sample_data())
    df2 = df.rename(columns={"open": "o", "close": "c"})
    assert "o" in df2.columns
    assert "o" not in df.columns

def test_concat_convert_and_to_datetime():
    df_a = DataFrame(data=[{"a": "1"}, {"a": "2"}])
    df_b = DataFrame(data=[{"a": "3"}])
    c = concat([df_a, df_b])
    assert len(c) == 3

    def cvt(x):
        return int(x)
    c = c.assign(a=lambda r: r["a"].apply(cvt) if hasattr(r["a"], "apply") else cvt(r["a"]))
    assert _to_list(c["a"]) == [1, 2, 3]

    c = concat([df_a, df_b])
    def ma(x):
        return "ma" + str(x)
    c = c.assign(a=lambda r: r["a"].apply(ma) if hasattr(r["a"], "apply") else ma(r["a"]))
    assert _to_list(c["a"]) == ["ma1", "ma2", "ma3"]

    res = to_datetime(["2020-01-01"])
    lst = res.tolist() if hasattr(res, "tolist") else res
    assert isinstance(lst[0], (datetime.datetime,)) or (
        importlib.util.find_spec("pandas") is not None and hasattr(lst[0], "to_pydatetime")
    )

    res = to_datetime(["20200102"], format="%Y%m%d")
    lst = res.tolist() if hasattr(res, "tolist") else res
    assert isinstance(lst[0], (datetime.datetime,))


if __name__ == "__main__":
    test_column_access_and_slice()
