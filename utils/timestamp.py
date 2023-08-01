def td_format(td_object):
    seconds = int(td_object.total_seconds())

    if seconds == 0:
        return "0 seconds"

    if seconds < 0:
        new_seconds = abs(seconds)
        periods = [
            ("year", 60 * 60 * 24 * 365),
            ("month", 60 * 60 * 24 * 30),
            ("day", 60 * 60 * 24),
            ("hour", 60 * 60),
            ("minute", 60),
            ("second", 1),
        ]

        strings = []
        for period_name, period_seconds in periods:
            if new_seconds >= period_seconds:
                period_value, new_seconds = divmod(new_seconds, period_seconds)
                has_s = "s" if period_value > 1 else ""
                strings.append("%s %s%s" % (period_value, period_name, has_s))
        if strings is not []:
            stri = ", ".join(strings)
            stri = "-" + stri
            return stri
        else:
            raise ValueError("Time delta is too small")

    periods = [
        ("year", 60 * 60 * 24 * 365),
        ("month", 60 * 60 * 24 * 30),
        ("day", 60 * 60 * 24),
        ("hour", 60 * 60),
        ("minute", 60),
        ("second", 1),
    ]

    strings = []
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            has_s = "s" if period_value > 1 else ""
            strings.append("%s %s%s" % (period_value, period_name, has_s))
    if strings is not []:
        return ", ".join(strings)
    else:
        raise ValueError("Time delta is too small")
