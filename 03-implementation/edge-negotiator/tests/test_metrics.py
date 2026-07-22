"""Tests for throughput-controlled metrics (src/metrics.py).

Run from the project root with the venv interpreter:
    .venv/Scripts/python -m pytest tests/test_metrics.py -v

These tests exist to BREAK the metrics. The centrepiece (TestSurvivorshipBias)
constructs the exact survivorship-bias failure mode (see the src/metrics.py module
docstring): a controller that completes FEWER but FASTER trips. The OLD completed-only average is fooled by it;
the assertions verify the NEW throughput-controlled metrics (total/mean network delay
and the matched-set diff) are NOT fooled. The rest covers completion-rate arithmetic,
parsing/boundary validation, immutability, and adversarial malformed input.
"""

import math
import os
import sys

import pytest

# src/ is not installed; put it on the path so `import metrics` resolves.
_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from metrics import (  # noqa: E402
    MetricsError,
    RunRecord,
    Trip,
    avg_travel_time_completed,
    completion_rate,
    matched_avg_travel_time,
    matched_completed_ids,
    matched_diff,
    mean_network_delay,
    parse_tripinfo,
    summary,
    throughput,
    total_network_delay,
)


# --------------------------------------------------------------------------- #
# Helpers: build tripinfo XML strings programmatically.                        #
# --------------------------------------------------------------------------- #
def _trip_xml(veh_id, depart, arrival, duration, waiting=0.0, time_loss=0.0,
              route_length=100.0):
    return (
        f'<tripinfo id="{veh_id}" depart="{depart:.2f}" arrival="{arrival:.2f}" '
        f'duration="{duration:.2f}" routeLength="{route_length:.2f}" '
        f'waitingTime="{waiting:.2f}" waitingCount="0" stopTime="0.00" '
        f'timeLoss="{time_loss:.2f}" rerouteNo="0" vType="DEFAULT_VEHTYPE"/>'
    )


def _doc(*trip_xmls):
    return '<tripinfos>' + ''.join(trip_xmls) + '</tripinfos>'


def _parse(*trips):
    return parse_tripinfo(_doc(*trips), from_string=True)


# A completed trip: arrival >= 0. An unfinished trip: arrival = -1, duration = accrued.
def completed(veh_id, depart, duration, **kw):
    return _trip_xml(veh_id, depart, depart + duration, duration, **kw)


def unfinished(veh_id, depart, accrued, **kw):
    return _trip_xml(veh_id, depart, -1.0, accrued, **kw)


def undeparted(veh_id, accrued=0.0):
    # depart = -1 (never entered); SUMO writes arrival = -1 too.
    return _trip_xml(veh_id, -1.0, -1.0, accrued)


# =========================================================================== #
# THE CENTRAL TEST: the survivorship-bias confound must be EXPOSED, not hidden #
# =========================================================================== #
class TestSurvivorshipBias:
    """A controller that completes fewer-but-faster trips must NOT look better
    under the throughput-controlled metrics."""

    def _build_pair(self):
        # Scenario: 5 vehicles depart in both runs.
        # RUN_GOOD (e.g. fixed-time): completes ALL 5, including two slow ones.
        #   durations: 20, 25, 30, 200, 220  (slow vehicles 3,4 do finish)
        run_good = _parse(
            completed("0", 0, 20),
            completed("1", 1, 25),
            completed("2", 2, 30),
            completed("3", 3, 200),
            completed("4", 4, 220),
        )
        # RUN_SPURIOUS (e.g. a controller that gridlocks the slow vehicles):
        #   completes ONLY the 3 fast ones (durations 20,25,30); the two slow
        #   vehicles are STILL RUNNING at the horizon, having already accrued
        #   300s and 320s in network (i.e. they are doing WORSE, not better).
        run_spurious = _parse(
            completed("0", 0, 20),
            completed("1", 1, 25),
            completed("2", 2, 30),
            unfinished("3", 3, 300),
            unfinished("4", 4, 320),
        )
        return run_good, run_spurious

    def test_old_metric_is_fooled(self):
        """Sanity: the OLD completed-only average DOES show the spurious 'win'.
        (If this didn't hold there'd be no confound to fix -- anti-tautology guard.)"""
        run_good, run_spurious = self._build_pair()
        old_good = avg_travel_time_completed(run_good)        # mean of 5: 99.0
        old_spurious = avg_travel_time_completed(run_spurious)  # mean of 3: 25.0
        assert old_spurious < old_good, (
            "the biased metric should LOOK better for the trip-stranding controller; "
            f"got spurious={old_spurious} good={old_good}")

    def test_throughput_exposes_it(self):
        run_good, run_spurious = self._build_pair()
        assert throughput(run_good) == 5
        assert throughput(run_spurious) == 3
        # Stranding trips LOWERS throughput -- it cannot be gamed.
        assert throughput(run_spurious) < throughput(run_good)

    def test_total_network_delay_exposes_it(self):
        run_good, run_spurious = self._build_pair()
        # GOOD: 20+25+30+200+220 = 495
        # SPURIOUS: 20+25+30 + 300+320 (accrued by stranded) = 695
        td_good = total_network_delay(run_good)
        td_spurious = total_network_delay(run_spurious)
        assert td_good == pytest.approx(495.0)
        assert td_spurious == pytest.approx(695.0)
        # The trip-stranding controller is WORSE on outstanding work, as it should be.
        assert td_spurious > td_good

    def test_mean_network_delay_exposes_it(self):
        run_good, run_spurious = self._build_pair()
        # Both have 5 departed vehicles: 495/5=99.0 vs 695/5=139.0
        assert mean_network_delay(run_good) == pytest.approx(99.0)
        assert mean_network_delay(run_spurious) == pytest.approx(139.0)
        assert mean_network_delay(run_spurious) > mean_network_delay(run_good)

    def test_matched_diff_is_not_fooled(self):
        run_good, run_spurious = self._build_pair()
        md = matched_diff(run_spurious, run_good)
        # Matched set = vehicles completed in BOTH = {0,1,2} (the fast ones).
        assert md["n_matched"] == 3
        # On the SHARED trips the two runs are identical (20,25,30), so the
        # apples-to-apples difference is ZERO -- no spurious improvement.
        assert md["avg_a"] == pytest.approx(25.0)
        assert md["avg_b"] == pytest.approx(25.0)
        assert md["diff_a_minus_b"] == pytest.approx(0.0)
        # And it records that 'good' completed 2 trips the spurious run did not.
        assert md["n_only_b"] == 2
        assert md["n_only_a"] == 0


# =========================================================================== #
# completion_rate arithmetic + boundaries                                      #
# =========================================================================== #
class TestCompletionRate:
    def test_basic_ratio(self):
        run = _parse(
            completed("0", 0, 10),
            completed("1", 1, 10),
            unfinished("2", 2, 50),
            unfinished("3", 3, 50),
        )
        # departed=4, completed=2 -> 0.5
        assert completion_rate(run) == pytest.approx(0.5)

    def test_undeparted_excluded_from_denominator(self):
        run = _parse(
            completed("0", 0, 10),
            unfinished("1", 1, 50),
            undeparted("2"),   # never entered -> not counted in departed
            undeparted("3"),
        )
        # departed = 2 (veh 0,1), completed = 1 -> 0.5; undeparted ignored.
        assert completion_rate(run) == pytest.approx(0.5)
        s = summary(run)
        assert s["departed"] == 2
        assert s["undeparted"] == 2
        assert s["loaded"] == 4

    def test_all_completed_rate_one(self):
        run = _parse(completed("0", 0, 10), completed("1", 1, 10))
        assert completion_rate(run) == pytest.approx(1.0)

    def test_nobody_departed_is_nan(self):
        run = _parse(undeparted("0"), undeparted("1"))
        assert math.isnan(completion_rate(run))
        assert math.isnan(mean_network_delay(run))
        assert total_network_delay(run) == 0.0
        assert throughput(run) == 0

    def test_empty_file(self):
        run = parse_tripinfo("<tripinfos/>", from_string=True)
        assert throughput(run) == 0
        assert math.isnan(avg_travel_time_completed(run))
        assert math.isnan(completion_rate(run))
        assert run.has_unfinished is False
        assert run.has_undeparted is False


# =========================================================================== #
# matched-set helper edge cases                                                #
# =========================================================================== #
class TestMatched:
    def test_no_overlap_returns_nan(self):
        a = _parse(completed("0", 0, 10))
        b = _parse(completed("1", 0, 10))
        assert matched_completed_ids(a, b) == ()
        md = matched_diff(a, b)
        assert md["n_matched"] == 0
        assert math.isnan(md["diff_a_minus_b"])

    def test_running_vehicle_not_in_matched_set(self):
        # veh 0 completes in a but is still running in b -> not matched.
        a = _parse(completed("0", 0, 10), completed("1", 0, 10))
        b = _parse(unfinished("0", 0, 99), completed("1", 0, 14))
        assert matched_completed_ids(a, b) == ("1",)
        md = matched_diff(a, b)
        assert md["n_matched"] == 1
        assert md["diff_a_minus_b"] == pytest.approx(10 - 14)

    def test_matched_avg_rejects_uncompleted_id(self):
        run = _parse(completed("0", 0, 10))
        with pytest.raises(MetricsError):
            matched_avg_travel_time(run, ("0", "missing"))

    def test_matched_avg_empty_ids_is_nan(self):
        run = _parse(completed("0", 0, 10))
        assert math.isnan(matched_avg_travel_time(run, ()))

    def test_diff_sign_convention(self):
        # a faster than b on the shared trip -> diff negative.
        a = _parse(completed("0", 0, 10))
        b = _parse(completed("0", 0, 30))
        md = matched_diff(a, b)
        assert md["diff_a_minus_b"] == pytest.approx(-20.0)


# =========================================================================== #
# Parsing / boundary validation (never trust the file)                         #
# =========================================================================== #
class TestParsing:
    def test_classifies_running_vs_completed_vs_undeparted(self):
        run = _parse(
            completed("c", 0, 10),
            unfinished("r", 1, 50),
            undeparted("u"),
        )
        assert run.has_unfinished is True
        assert run.has_undeparted is True
        assert {t.veh_id for t in run.completed_trips} == {"c"}
        assert {t.veh_id for t in run.running_trips} == {"r"}
        assert {t.veh_id for t in run.undeparted_trips} == {"u"}
        assert {t.veh_id for t in run.departed_trips} == {"c", "r"}

    def test_legacy_file_has_no_unfinished_flag(self):
        # Legacy style: completed-only. Flag must be False so callers
        # know completion_rate is untrustworthy (collapses to 1.0).
        run = _parse(completed("0", 0, 10), completed("1", 1, 20))
        assert run.has_unfinished is False
        assert completion_rate(run) == pytest.approx(1.0)  # but meaningless
        assert summary(run)["write_unfinished_present"] == 0.0

    def test_duplicate_id_rejected(self):
        with pytest.raises(MetricsError, match="duplicate"):
            _parse(completed("0", 0, 10), completed("0", 1, 20))

    def test_missing_id_rejected(self):
        bad = '<tripinfos><tripinfo depart="0.00" arrival="10.00" duration="10.00" ' \
              'routeLength="1.0" waitingTime="0.0" timeLoss="0.0"/></tripinfos>'
        with pytest.raises(MetricsError, match="id"):
            parse_tripinfo(bad, from_string=True)

    def test_missing_required_attr_rejected(self):
        bad = '<tripinfos><tripinfo id="0" depart="0.00" arrival="10.00"/></tripinfos>'
        with pytest.raises(MetricsError, match="missing required"):
            parse_tripinfo(bad, from_string=True)

    def test_non_numeric_attr_rejected(self):
        bad = '<tripinfos><tripinfo id="0" depart="0.00" arrival="x" duration="10.00" ' \
              'routeLength="1.0" waitingTime="0.0" timeLoss="0.0"/></tripinfos>'
        with pytest.raises(MetricsError, match="not a number"):
            parse_tripinfo(bad, from_string=True)

    def test_nan_inf_rejected(self):
        for bad_val in ("nan", "inf", "-inf"):
            bad = (f'<tripinfos><tripinfo id="0" depart="0.00" arrival="10.00" '
                   f'duration="{bad_val}" routeLength="1.0" waitingTime="0.0" '
                   f'timeLoss="0.0"/></tripinfos>')
            with pytest.raises(MetricsError, match="NaN/Inf"):
                parse_tripinfo(bad, from_string=True)

    def test_negative_duration_for_departed_rejected(self):
        bad = ('<tripinfos><tripinfo id="0" depart="0.00" arrival="10.00" '
               'duration="-5.00" routeLength="1.0" waitingTime="0.0" '
               'timeLoss="0.0"/></tripinfos>')
        with pytest.raises(MetricsError, match="negative duration"):
            parse_tripinfo(bad, from_string=True)

    def test_arrival_before_depart_rejected(self):
        bad = ('<tripinfos><tripinfo id="0" depart="50.00" arrival="10.00" '
               'duration="10.00" routeLength="1.0" waitingTime="0.0" '
               'timeLoss="0.0"/></tripinfos>')
        with pytest.raises(MetricsError, match="precedes depart"):
            parse_tripinfo(bad, from_string=True)

    def test_malformed_xml_rejected(self):
        with pytest.raises(MetricsError, match="could not parse"):
            parse_tripinfo("<tripinfos><tripinfo", from_string=True)


# =========================================================================== #
# Immutability                                                                 #
# =========================================================================== #
class TestImmutability:
    def test_trip_is_frozen(self):
        t = Trip("0", 0.0, 10.0, 10.0, 0.0, 0.0, 100.0)
        with pytest.raises(Exception):
            t.duration = 5.0  # type: ignore[misc]

    def test_runrecord_is_frozen(self):
        run = _parse(completed("0", 0, 10))
        with pytest.raises(Exception):
            run.trips = ()  # type: ignore[misc]

    def test_partitions_return_tuples(self):
        run = _parse(completed("0", 0, 10), unfinished("1", 1, 50))
        assert isinstance(run.completed_trips, tuple)
        assert isinstance(run.departed_trips, tuple)
        assert isinstance(run.running_trips, tuple)
