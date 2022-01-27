# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""Module for pre-defined widget layouts."""
from datetime import datetime, timedelta

import ipywidgets as widgets
from ipywidgets import Layout

from ..._version import VERSION
from ...common.timespan import TimeSpan
from ...common.utility import check_kwargs
from .core import (
    IPyDisplayMixin,
    RegisteredWidget,
    TimeUnit,
    default_before_after,
    default_max_buffer,
    parse_time_unit,
)

__version__ = VERSION
__author__ = "Ian Hellen"


# pylint: disable=too-many-instance-attributes
class QueryTime(RegisteredWidget, IPyDisplayMixin):
    """
    QueryTime.

    Composite widget to capture date and time origin
    and set start and end times for queries.

    See Also
    --------
    RegisteredWidget

    """

    _ALLOWED_KWARGS = [
        "origin_time",
        "before",
        "after",
        "start",
        "end",
        "max_before",
        "max_after",
        "label",
        "description",
        "units",
        "auto_display",
        "timespan",
        "register",
    ]

    _label_style = {"description_width": "initial"}

    IDS_ATTRIBS = [
        "origin_time",
        "before",
        "after",
        "_query_start",
        "_query_end",
        "_label",
    ]

    def __init__(
        self,
        **kwargs,
    ):
        """
        Create new instance of QueryTime.

        Parameters
        ----------
        origin_time : datetime, optional
            The origin time (the default is `datetime.utcnow()`)
        description : str, optional
            The description to display
            (the default is 'Select time ({units}) to look back')
            label is an alias for this parameter
        before : int, optional
            The default number of `units` before the `origin_time`
            (the default varies based on the unit)
        after : int, optional
            The default number of `units` after the `origin_time`
            (the default varies based on the unit)
        start : Union[datetime, str]
            Start of query time - alternative to specifying origin,
            before, after
        end : Union[datetime, str]
            End of query time - alternative to specifying origin,
            before, after
        timespan : TimeSpan
            TimeSpan of query time - alternative to specifying origin,
            before, after
        max_before : int, optional
            The largest value for `before` (the default varies based on the unit)
        max_after : int, optional
            The largest value for `after` (the default varies based on the unit)
        units : str, optional
            Time unit (the default is 'hour')
            Permissable values are 'day', 'hour', 'minute', 'second',
            'week'
            These can all be abbreviated down to initial characters
            ('d', 'm', etc.)
        auto_display : bool, optional
            Whether to display on instantiation (the default is False)

        """
        check_kwargs(kwargs, self._ALLOWED_KWARGS)
        self._label = kwargs.pop(
            "description", kwargs.pop("label", "Set query time boundaries")
        )
        self._time_unit = parse_time_unit(kwargs.get("units", "min"))

        self.before = kwargs.pop("before", None)
        self.after = kwargs.pop("after", None)
        self._query_start = self._query_end = self.origin_time = datetime.utcnow
        self._get_time_parameters(**kwargs)

        self.max_before = kwargs.pop("max_before", None)
        self.max_after = kwargs.pop("max_after", None)
        self._adjust_max_before_after(self.max_before, self.max_after)

        # Call superclass to register
        ids_params = [
            self.origin_time,
            self.before,
            self.after,
            self.max_before,
            self.max_after,
            self._label,
            self._time_unit,
        ]

        super().__init__(id_vals=ids_params, val_attrs=self.IDS_ATTRIBS, **kwargs)

        # Create widgets
        self._w_origin_dt = widgets.DatePicker(
            description="Origin Date", disabled=False, value=self.origin_time.date()
        )
        self._w_origin_tm = widgets.Text(
            description="Time (24hr)",
            disabled=False,
            value=str(self.origin_time.time()),
        )

        range_desc = "Time Range"
        self._w_tm_range = widgets.IntRangeSlider(
            value=(-self.before, self.after),
            min=-self.max_before,
            max=self.max_after,
            step=1,
            description=range_desc,
            disabled=False,
            continuous_update=True,
            orientation="horizontal",
            readout=True,
            readout_format="d",
            layout=Layout(width="70%"),
            style=self._label_style,
        )
        # pylint: disable=no-member
        self._w_time_unit = widgets.Dropdown(
            options=[
                unit.capitalize()
                for unit, _ in TimeUnit.__members__.items()
                if unit != "Second"
            ],
            value=self._time_unit.name.capitalize(),
            layout=Layout(width="100px"),
        )
        # pylint: enable=no-member

        self._w_start_time_txt = widgets.Text(
            value=self._query_start.isoformat(sep=" "),
            description="Query start time (UTC):",
            layout=Layout(width="50%"),
            style=self._label_style,
        )
        self._w_end_time_txt = widgets.Text(
            value=self._query_end.isoformat(sep=" "),
            description="Query end time (UTC) :  ",
            layout=Layout(width="50%"),
            style=self._label_style,
        )

        # Add change event handlers
        self._w_tm_range.observe(self._time_range_change, names="value")
        self._w_origin_dt.observe(self._update_origin, names="value")
        self._w_origin_tm.observe(self._update_origin, names="value")
        self._w_time_unit.observe(self._change_time_unit, names="value")

        self.layout = self._create_layout()
        if kwargs.pop("auto_display", False):
            self.display()

    def _create_layout(self):
        return widgets.VBox(
            [
                widgets.HTML(f"<h4>{self._label}</h4>"),
                widgets.HBox([self._w_origin_dt, self._w_origin_tm]),
                widgets.VBox(
                    [
                        widgets.HBox([self._w_tm_range, self._w_time_unit]),
                        self._w_start_time_txt,
                        self._w_end_time_txt,
                    ]
                ),
            ]
        )

    def _change_time_unit(self, change):
        """Reset before/after and max buffers to defaults."""
        unit = change["new"]
        self._time_unit = parse_time_unit(unit)
        self.before = default_before_after(default=None, unit=self._time_unit)
        self.after = default_before_after(default=None, unit=self._time_unit)
        self._adjust_max_before_after(max_before=None, max_after=None)
        self._w_tm_range.value = (-self.before, self.after)
        self._w_tm_range.min = -self.max_before
        self._w_tm_range.max = self.max_after

    def _get_time_parameters(self, **kwargs):
        """Process different init time parameters."""
        timespan: TimeSpan = kwargs.pop("timespan", None)
        start = kwargs.pop("start", None)
        end = kwargs.pop("end", None)
        if timespan:
            self._query_end = self.origin_time = timespan.end
            self._query_start = timespan.start
        elif start and end:
            timespan = TimeSpan(start=start, end=end)
            self._query_start = timespan.start
            self._query_end = self.origin_time = timespan.end
        else:
            self.origin_time = kwargs.pop("origin_time", datetime.utcnow())
            self.before = default_before_after(self.before, self._time_unit)
            self.after = default_before_after(self.after, self._time_unit)
            # Calculate time offsets from origin
            self._query_start = self.origin_time - timedelta(
                0, self.before * self._time_unit.value
            )
            self._query_end = self.origin_time + timedelta(
                0, self.after * self._time_unit.value
            )
            timespan = TimeSpan(start=self._query_start, end=self._query_end)
        if "units" not in kwargs:
            self._infer_time_units()
        if self.after is None:
            self.after = 0
        if self.before is None:
            self.before = int(
                (self._query_end - self._query_start).total_seconds()
                / self._time_unit.value
            )

    def _infer_time_units(self):
        # If time units not set explicitly, set to something sensible,
        # based on start/end times
        if abs(self.timespan.period.days) > 1:
            self._time_unit = TimeUnit.DAY
        elif abs(self.timespan.period.total_seconds()) > 3600:
            self._time_unit = TimeUnit.HOUR
        else:
            self._time_unit = TimeUnit.MINUTE

    def _adjust_max_before_after(self, max_before, max_after):
        """Adjust the max values so the are always bigger than the defaults."""
        self.max_before = default_max_buffer(
            max_before, self.before or 1, self._time_unit
        )
        self.max_after = default_max_buffer(max_after, self.after or 1, self._time_unit)

    def _update_origin(self, change):
        del change
        try:
            tm_value = datetime.strptime(self._w_origin_tm.value, "%H:%M:%S.%f").time()
            self.origin_time = datetime.combine(self._w_origin_dt.value, tm_value)
            self._time_range_change(change=None)
        except (ValueError, TypeError):
            # reset on error
            self._w_origin_dt.value = self.origin_time.date()
            self._w_origin_tm = self.origin_time.time()

    def _time_range_change(self, change):
        del change
        self._query_start = self.origin_time + timedelta(
            0, self._w_tm_range.value[0] * self._time_unit.value
        )
        self._query_end = self.origin_time + timedelta(
            0, self._w_tm_range.value[1] * self._time_unit.value
        )
        self._w_start_time_txt.value = self._query_start.isoformat(sep=" ")
        self._w_end_time_txt.value = self._query_end.isoformat(sep=" ")
        self.before = abs(self._w_tm_range.value[0])
        self.after = abs(self._w_tm_range.value[1])

    @property
    def start(self):
        """Query start time."""
        return self._query_start

    @property
    def end(self):
        """Query end time."""
        return self._query_end

    @property
    def units(self):
        """Time units used by control."""
        return self._time_unit.name.capitalize()

    @property
    def timespan(self):
        """Return the timespan as a TimeSpan object."""
        return TimeSpan(start=self.start, end=self.end)

    @property
    def value(self):
        """Return the timespan as a TimeSpan object."""
        return self.timespan
