from .core import baseline_digest


def sample_case(kind="drift"):
    initial = {"mode":"safe","count":0,"audit":[]}
    expected = {"mode":"safe","count":0,"audit":[]}
    events = [
        {"event_id":"e1","op":"set","path":"mode","value":"safe"},
        {"event_id":"e2","op":"set","path":"count","value":0},
        {"event_id":"e3","op":"set","path":"mode","value":"unsafe"},
        {"event_id":"e4","op":"set","path":"count","value":0}
    ]
    case = {"schema":"drift-isolator-case/1.0","case_id":"DI-DEMO-001","initial_state":initial,"expected_state":expected,"baseline_sha256":baseline_digest(initial,expected),"events":events}
    if kind == "no-drift": case["events"] = events[:2]
    elif kind == "invalid-baseline": case["baseline_sha256"] = "0" * 64
    elif kind != "drift": raise ValueError(kind)
    return case
