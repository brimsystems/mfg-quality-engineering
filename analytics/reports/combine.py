"""Two study builders as one report: sections and tables numbered through, one recommendation, one method note, one appendix."""
import re

from analytics.style.style import DOCS, report_shell

REPORTS = {
    "measurement": ("measurement_and_capability", "Measurement systems and process capability", "the measurement report"),
    "root_cause": ("root_cause_and_doe", "Root cause and designed experiment", "the root cause report"),
    "supplier": ("supplier_and_cost_of_quality", "Supplier quality and cost of quality", "the supplier report"),
}
SHOP = "Precision machining shop, about 150 employees, IATF 16949 and AS9100, one plant. "
TABLES = re.compile(r"\b(Tables?) (A?\d+(?:(?:, | and | to )A?\d+)*)")


def split(body):
    """A builder's page body as its sections, recommendation, method note and appendix."""
    i, j, k = body.index("<h2 id='rec'>"), body.index("<h2 id='method'>"), body.index("<h2 id='app'>")
    strip = lambda s: re.sub(r"^<h2 id='\w+'>.*?</h2>", "", s, count=1, flags=re.S)
    return {"sections": body[:i], "rec": strip(body[i:j]), "method": strip(body[j:k]), "appendix": strip(body[k:])}


def table_counts(body):
    plain = [int(x) for x in re.findall(r"\bTable (\d+)\.", body)]
    lettered = [int(x) for x in re.findall(r"\bTable A(\d+)\.", body)]
    return max(plain, default=0), max(lettered, default=0)


def renumber_tables(s, base, body_tables):
    """Body tables keep their order from `base`; the appendix tables follow them, without their letter."""
    token = lambda t: str(base + body_tables + int(t[1:])) if t.startswith("A") else str(base + int(t))
    return TABLES.sub(lambda m: m.group(1) + " " + re.sub(r"A?\d+", lambda d: token(d.group(0)), m.group(2)), s)


def shift_sections(s, by):
    return re.sub(r"<h2 id='f(\d+)'>(\d+)\. ", lambda m: f"<h2 id='f{int(m.group(1)) + by}'>{int(m.group(2)) + by}. ", s)


def chart_titles(s):
    """Each figure under a title, which is its alt text, with no numbered caption line."""
    s = re.sub(r"(<img alt=\"([^\"]*)\"[^>]*>)\s*<div class=\"caption\">Figure \d+\.[^<]*</div>", r"<div class='chart-title'>\2</div>\1", s)
    assert not re.search(r"Figure \d", s), re.findall(r".{60}Figure \d.{40}", s)[:3]
    return s


def recommendation(rec):
    """The recommendation text apart from its target line, countermeasures rows and follow-up line."""
    target = re.search(r"<p>Target: (.*?)</p>", rec, flags=re.S)
    follow = re.search(r"<p>Follow-up: (.*?)</p>", rec, flags=re.S)
    tab = re.search(r"<table class=\"data\"><thead>.*?</thead><tbody>(.*?)</tbody></table>", rec[target.end():], flags=re.S) if target else None
    text = rec
    for m in (target, follow):
        if m:
            text = text.replace(m.group(0), "")
    if tab:
        text = text.replace(tab.group(0), "")
    return text, target.group(1) if target else None, tab.group(1) if tab else "", follow.group(1) if follow else None


def unique_sentences(second, first):
    dropped = []

    def keep(m):
        t = m.group(0)
        if len(t.strip()) > 40 and t.strip() in first:
            dropped.append(t.strip())
            return ""
        return t
    return re.sub(r"[^.<>]+(?:\.(?!\s|<|$)[^.<>]*)*\.(?:\s+|(?=<)|$)", keep, second), dropped


def header(m1, m2):
    """One header for the two halves: the shop line once, the sources of both, the customer package elements of both."""
    a, b = m1.split("<br>"), m2.split("<br>")
    scope1, scope2 = a[0].replace(SHOP, "", 1).rstrip("."), b[0].replace(SHOP, "", 1).rstrip(".")
    period, _, detail1 = scope1.partition("; ")
    detail2 = scope2.partition("; ")[2]
    details = [d for d in (detail1, detail2) if d]
    details = details[:1] if len(details) == 2 and details[0] == details[1] else details
    line1 = SHOP + period + ("; " + "; ".join(details) if details else "") + "."
    line2 = a[1].rstrip(".") + "; " + b[1].replace("Sources: ", "", 1)
    return "<br>".join([line1, line2, a[2] + " " + b[2]])


def references(body):
    """Another report by its full title at its first mention in the text, and by its short name after that and in every table cell; each a link."""
    seen = set()

    def one(m):
        stem, title, short = REPORTS[m.group(1)]
        before = body[:m.start()]
        in_cell = before.rfind("<td") > before.rfind("</td>")
        if not in_cell and m.group(1) not in seen:
            seen.add(m.group(1))
            return f"<a href='{stem}.html'>{title}</a>"
        opens = before.rstrip()[-1:] in (".", ">", "")
        return f"<a href='{stem}.html'>{short[0].upper() + short[1:] if opens else short}</a>"
    return re.sub(r"\[\[R:(\w+)\]\]", one, body)


def write(key, first, second, titles, lead):
    stem, title, _ = REPORTS[key]
    a, b = first.build(), second.build()
    n1, k1 = table_counts(a["body"])
    n2, k2 = table_counts(b["body"])
    A = {p: renumber_tables(v, 0, n1) for p, v in split(a["body"]).items()}
    B = {p: renumber_tables(v, n1 + k1, n2) for p, v in split(b["body"]).items()}
    n_first = len(re.findall(r"<h2 id='f\d+'>", A["sections"]))
    n_second = len(re.findall(r"<h2 id='f\d+'>", B["sections"]))
    B["sections"] = shift_sections(B["sections"], n_first)
    B["sections"] = re.sub(r"(<h2 id='f\d+'>.*?</h2>)", rf"\1<p class='lead'>{lead}</p>", B["sections"], count=1, flags=re.S)
    (text1, t1, rows1, f1), (text2, t2, rows2, f2) = recommendation(A["rec"]), recommendation(B["rec"])
    rec = text1 + text2 + "".join(f"<p>Target: {t}</p>" for t in (t1, t2) if t)
    if rows1 or rows2:
        rec += f'<table class="data"><thead><tr><th>Action</th><th>Owner</th><th>When</th></tr></thead><tbody>{rows1}{rows2}</tbody></table>'
    if f1 or f2:
        rec += "<p>Follow-up: " + " ".join(x for x in (f1, f2) if x) + "</p>"
    method2, dropped = unique_sentences(B["method"], A["method"])
    body = "".join([
        A["sections"], B["sections"],
        "<h2 id='rec'>Recommendation</h2>", rec,
        "<h2 id='method'>Method and data</h2>", f"<h3>{titles[0]}</h3>", A["method"], f"<h3>{titles[1]}</h3>", method2,
        "<h2 id='app'>Appendix</h2>", A["appendix"], B["appendix"]])
    body = chart_titles(body)
    span = {"first": (1, n_first), "second": (n_first + 1, n_first + n_second)}
    body = re.sub(r"\[\[S:(\w+)\]\]", lambda m: f"<a href='#f{span[m.group(1)][0]}'>Sections {span[m.group(1)][0]} to {span[m.group(1)][1]}</a>", body)
    body = references(body)
    assert "[[" not in body
    toc = (list(a["toc"]) + [(f"f{int(i[1:]) + n_first}", t) for i, t in b["toc"]]
           + [("rec", "Recommendation"), ("method", "Method"), ("app", "Appendix")])
    out = DOCS / "reports"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{stem}.html").write_text(report_shell(title, "Study report", header(a["meta"], b["meta"]), body, toc), encoding="utf8", newline="\n")
    print(f"wrote docs/reports/{stem}.html: sections 1 to {n_first} and {n_first + 1} to {n_first + n_second}; tables 1 to {n1 + k1} and {n1 + k1 + 1} to {n1 + k1 + n2 + k2}; "
          f"method sentences stated once: {len(dropped)}")
    return out / f"{stem}.html"
