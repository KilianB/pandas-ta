# -*- coding: utf-8 -*-
import numpy as np
from numpy import isnan
from pandas import DataFrame, Series
from pandas_ta._typing import DictLike, Int, IntFloat
from pandas_ta.ma import ma
from pandas_ta.utils import (
    v_drift,
    v_mamode,
    v_offset,
    v_pos_default,
    v_scalar,
    v_series,
    zero
)
from pandas_ta.volatility import atr


def adx(
    high: Series, low: Series, close: Series,
    length: Int = None, lensig: Int = None, scalar: IntFloat = None,
    mamode: str = None, drift: Int = None,
    offset: Int = None, **kwargs: DictLike
) -> DataFrame:
    """Average Directional Movement (ADX)

    Average Directional Movement is meant to quantify trend strength by
    measuring the amount of movement in a single direction.

    Sources:
        TA Lib Correlation: >99%
        https://www.tradingtechnologies.com/help/x-study/technical-indicator-definitions/average-directional-movement-adx/

    Args:
        high (pd.Series): Series of 'high's
        low (pd.Series): Series of 'low's
        close (pd.Series): Series of 'close's
        length (int): It's period. Default: 14
        lensig (int): Signal Length. Like TradingView's default ADX.
            Default: length
        scalar (float): How much to magnify. Default: 100
        mamode (str): See ``help(ta.ma)``. Default: 'rma'
        drift (int): The difference period. Default: 1
        offset (int): How many periods to offset the result. Default: 0

    Kwargs:
        fillna (value, optional): pd.DataFrame.fillna(value)
        fill_method (value, optional): Type of fill method

    Returns:
        pd.DataFrame: adx, dmp, dmn columns.
    """
    # Validate
    length = v_pos_default(length, 14)
    lensig = v_pos_default(lensig, length)
    _length = max(length, lensig)
    high = v_series(high, _length)
    low = v_series(low, _length)
    close = v_series(close, _length)

    if high is None or low is None or close is None:
        return

    scalar = v_scalar(scalar, 100)
    mamode = v_mamode(mamode, "rma")
    drift = v_drift(drift)
    offset = v_offset(offset)

    # Calculate
    atr_ = atr(
        high=high, low=low, close=close,
        length=length, prenan=kwargs.pop("prenan", True)
    )
    if atr_ is None or all(isnan(atr_)):
        return

    up = high - high.shift(drift)  # high.diff(drift)
    dn = low.shift(drift) - low    # low.diff(-drift).shift(drift)

    pos = ((up > dn) & (up > 0)) * up
    neg = ((dn > up) & (dn > 0)) * dn

    pos = pos.apply(zero)
    neg = neg.apply(zero)

    # How to treat the initial value of RMA varies one to another.
    # It follows the way TradingView does, setting it to the average of previous values.
    # Since 'pandas' does not provide API to control the initial value,
    # work around it by modifying input value to get desired output.
    pos.iloc[length-1] = pos[:length].sum()
    pos[:length-1] = 0
    neg.iloc[length-1] = neg[:length].sum()
    neg[:length-1] = 0

    k = scalar / atr_
    alpha = 1 / length
    dmp = k * pos.ewm(alpha=alpha, adjust=False, min_periods=length).mean()
    dmn = k * neg.ewm(alpha=alpha, adjust=False, min_periods=length).mean()

    # The same goes with dx.
    dx = scalar * (dmp - dmn).abs() / (dmp + dmn)
    dx = dx.shift(-length)
    dx.iloc[length-1] = dx[:length].sum()
    dx[:length-1] = 0

    adx = ma(mamode, dx, length=lensig)
    # Rollback shifted rows.
    adx[: length - 1] = np.nan
    adx = adx.shift(length)

    # Offset
    if offset != 0:
        dmp = dmp.shift(offset)
        dmn = dmn.shift(offset)
        adx = adx.shift(offset)

    # Fill
    if "fillna" in kwargs:
        adx.fillna(kwargs["fillna"], inplace=True)
        dmp.fillna(kwargs["fillna"], inplace=True)
        dmn.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        adx.fillna(method=kwargs["fill_method"], inplace=True)
        dmp.fillna(method=kwargs["fill_method"], inplace=True)
        dmn.fillna(method=kwargs["fill_method"], inplace=True)

    # Name and Category
    adx.name = f"ADX_{lensig}"
    dmp.name = f"DMP_{length}"
    dmn.name = f"DMN_{length}"
    adx.category = dmp.category = dmn.category = "trend"

    data = {adx.name: adx, dmp.name: dmp, dmn.name: dmn}
    adxdf = DataFrame(data)
    adxdf.name = f"ADX_{lensig}"
    adxdf.category = "trend"

    return adxdf
