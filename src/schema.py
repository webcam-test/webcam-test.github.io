"""
JSON-LD for every page: one linked @graph per page (emitted in <head>), built here so all pages share the same entity ids.
Ported from MouseTester's src/schema.py (coffee_can_checker_tools_project/individual_websites/mousetester), which was
itself ported from company-marketcap.github.io. Same nodes and links; the author is Vinitha Pu (content/author.json).

Every graph carries the sitewide nodes (WebSite, and the author Person, who is both content author and fact checker) plus
the page's own nodes, tied together by @id references:

    WebSite  <-- isPartOf --  WebPage (or AboutPage / ContactPage / ProfilePage / CollectionPage)
    WebPage  -- breadcrumb --> BreadcrumbList, -- mainEntity --> WebApplication
    WebPage  -- author / reviewedBy --> Person
    WebApplication, HowTo, Article, FAQPage all point back at the WebPage with isPartOf / mainEntityOfPage

There is no Organization node: the site is run by an individual, so the Person is the publisher.
Dates are full ISO 8601 timestamps with a time zone. They come from git history (first and last commit of the page's
source file; see load_git_dates()), unless the page JSON sets "date_published" / "date_modified".

Site-specific differences from MouseTester: URLs are extensionless with no trailing slash (/<slug>, home = /), every
tool page (guides included) has an interactive card, so every tool page gets a WebApplication; applicationCategory is
split (see MULTIMEDIA_TOOLS); HowTo steps link to the tool card (#tool).
"""
import re
import subprocess
from datetime import date, datetime

TAG_RE = re.compile(r"<[^>]+>")
H2_RE = re.compile(r"<h2[^>]*>(.*?)</h2>", re.S)
OL_RE = re.compile(r"<ol[^>]*>(.*?)</ol>", re.S)
LI_RE = re.compile(r"<li[^>]*>(.*?)</li>", re.S)
PAGE_TYPES = {"about": "AboutPage", "contact": "ContactPage", "sitemap": "CollectionPage"}
# applicationCategory: tools that create media are MultimediaApplication; every test, checker and guide (most of the
# site) diagnoses hardware, so it's UtilitiesApplication (as on MouseTester).
MULTIMEDIA_TOOLS = {"webcam-video-recorder-online", "webcam-photo-capture-online", "webcam-gif-maker-online",
                    "webcam-timelapse-maker-online", "webcam-live-filter-preview"}


def text(fragment):
    return " ".join(re.sub(r"\s+", " ", TAG_RE.sub(" ", fragment)).replace("&amp;", "&").replace("&#x27;", "'").split())


def load_git_dates(site_dir):
    """{repo-relative path (src/content/x.json): (first commit time, last commit time)} as ISO 8601 with offset."""
    try:
        out = subprocess.run(["git", "log", "--format=@%cI", "--name-only", "--", "src/content", "src/build_data.py"],
                             cwd=site_dir, capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return {}
    dates, current = {}, None
    for line in out.splitlines():
        if line.startswith("@"):
            current = line[1:]
        elif line.strip():
            first, last = dates.get(line, (None, None))
            dates[line] = (current, last or current)  # log is newest first: oldest seen wins "first"
    return dates


def long_date(iso):
    d = date.fromisoformat(iso[:10])
    return f"{d:%B} {d.day}, {d.year}"


class Schema:
    def __init__(self, site, author, git_dates):
        self.site, self.author, self.git_dates = site, author, git_dates
        self.base = "https://" + site["domain"]
        self.website_id = f"{self.base}/#website"
        self.person_id = f"{self.base}/{author['slug']}#person"

    def stamp(self, value):
        """A date-only override becomes a full timestamp in the site's time zone."""
        return f"{value}T00:00:00{self.site['timezone_offset']}" if len(value) == 10 else value

    def dates(self, source_path, content=None):
        """(published, modified) timestamps for a source file. The page JSON can set date_published / date_modified;
        otherwise git history, falling back to now for files that aren't committed yet."""
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        first, last = self.git_dates.get(source_path, (None, None))
        content = content or {}
        published = self.stamp(content["date_published"]) if content.get("date_published") else first or now
        modified = self.stamp(content["date_modified"]) if content.get("date_modified") else last or now
        return published, max(published, modified)

    # --- sitewide nodes ---
    def website(self):
        s = self.site
        return {"@type": "WebSite", "@id": self.website_id, "url": self.base + "/", "name": s["site_name"],
                "description": s["footer_tagline"], "inLanguage": "en-US",
                "publisher": {"@id": self.person_id}, "creator": {"@id": self.person_id},
                "image": {"@type": "ImageObject", "@id": f"{self.base}/#icon",
                          "url": f"{self.base}/favicon.ico",
                          "contentUrl": f"{self.base}/favicon.ico", "width": 96, "height": 96,
                          "encodingFormat": "image/x-icon", "caption": f"{s['site_name']} logo"}}

    def person(self):
        a = self.author
        node = {"@type": "Person", "@id": self.person_id, "name": a["name"], "url": f"{self.base}/{a['slug']}",
                "jobTitle": a["job_title"], "description": a["bio"], "knowsAbout": a["knows_about"],
                "knowsLanguage": a.get("knows_language", []), "email": a["email"], "sameAs": a["same_as"],
                "alumniOf": [{"@type": e.get("school_type", "EducationalOrganization"), "name": e["school"],
                              "address": e["place"]}
                             for e in a["education"] if e.get("school_type") == "CollegeOrUniversity"],
                "hasCredential": [dict({"@type": "EducationalOccupationalCredential", "name": e["credential"],
                                        "credentialCategory": e["category"],
                                        "recognizedBy": {"@type": e.get("school_type", "EducationalOrganization"),
                                                         "name": e["school"], "address": e["place"]},
                                        "dateCreated": e["year"]},
                                       **({"educationalLevel": e["level"]} if e.get("level") else {}))
                                  for e in a["education"]]}
        if a.get("experience"):
            node["worksFor"] = [{"@type": "Organization", "name": w["organization"],
                                 "address": {"@type": "PostalAddress", "addressLocality": w["locality"],
                                             "addressCountry": w["country"]}} for w in a["experience"]]
        return node

    # --- page nodes ---
    def webpage(self, url, name, description, published=None, modified=None, kind="WebPage", extra=None, credit=True):
        node = {"@type": kind, "@id": url + "#webpage", "url": url, "name": name, "headline": name,
                "description": description, "inLanguage": "en-US", "isPartOf": {"@id": self.website_id},
                "publisher": {"@id": self.person_id}, "breadcrumb": {"@id": url + "#breadcrumb"},
                "potentialAction": {"@type": "ReadAction", "target": [url]}}
        if published:  # pages with no visible date (404) carry none in the markup either
            node["datePublished"], node["dateModified"] = published, modified
        if credit:
            node["author"] = {"@id": self.person_id}
            node["reviewedBy"] = {"@id": self.person_id}
        node.update(extra or {})
        return node

    def breadcrumb(self, url, trail):
        """trail: [(name, path)], the last item may have path None (the current page)."""
        return {"@type": "BreadcrumbList", "@id": url + "#breadcrumb", "itemListElement": [
            {"@type": "ListItem", "position": i, "name": name, "item": self.base + link if link else url}
            for i, (name, link) in enumerate(trail, 1)]}

    def faq(self, url, faq):
        if not faq:
            return []
        return [{"@type": "FAQPage", "@id": url + "#faq", "isPartOf": {"@id": url + "#webpage"}, "inLanguage": "en-US",
                 "mainEntity": [{"@type": "Question", "name": text(qa["question"]),
                                 "acceptedAnswer": {"@type": "Answer", "text": text(qa["answer"])}} for qa in faq]}]

    def item_list(self, url, ident, name, items):
        return {"@type": "ItemList", "@id": f"{url}#{ident}", "name": name, "numberOfItems": len(items),
                "itemListElement": [{"@type": "ListItem", "position": i, "name": n, "url": self.base + u}
                                    for i, (n, u) in enumerate(items, 1)]}

    def howto(self, url, name, content):
        """HowTo from the article's own 'How to ...' section: the first <ol> after an <h2> that starts 'How to'."""
        for sec in re.split(r"(?=<h2)", content):
            m = H2_RE.match(sec)
            if not (m and re.match(r"\s*how to\b", text(m.group(1)), re.I)):
                continue
            ol = OL_RE.search(sec)
            steps = [text(li) for li in LI_RE.findall(ol.group(1))] if ol else []
            if not steps:
                continue
            return {"@type": "HowTo", "@id": url + "#howto", "name": text(m.group(1)), "inLanguage": "en-US",
                    "isPartOf": {"@id": url + "#webpage"}, "tool": {"@type": "HowToTool", "name": name},
                    "step": [{"@type": "HowToStep", "position": i, "name": re.split(r"(?<=[.!?])\s", t, 1)[0][:110],
                              "text": t, "url": url + "#tool"} for i, t in enumerate(steps, 1)]}
        return None

    # --- page types ---
    def tool(self, tool, url, trail, published, modified):
        """Tool pages: a WebPage whose mainEntity is the WebApplication, plus HowTo, Article and FAQPage."""
        name, desc = tool["h1"], tool["meta_description"]
        content = (tool.get("content_html") or "").strip()
        main_id = url + "#webapplication"
        page = self.webpage(url, tool["h1"], desc, published, modified,
                            extra={"mainEntity": {"@id": main_id}, "about": {"@id": main_id}})
        graph = [self.website(), self.person(), page, self.breadcrumb(url, trail or [("Home", "/")]),
                 {"@type": "WebApplication", "@id": main_id, "name": name, "url": url, "description": desc,
                  "applicationCategory": "MultimediaApplication" if tool["slug"] in MULTIMEDIA_TOOLS
                  else "UtilitiesApplication", "operatingSystem": "Any",
                  "browserRequirements": "Requires JavaScript and camera/microphone permissions where applicable. "
                                         "Works in any modern browser.",
                  "isAccessibleForFree": True, "inLanguage": "en-US",
                  "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
                  "isPartOf": {"@id": url + "#webpage"}, "author": {"@id": self.person_id},
                  "creator": {"@id": self.person_id}, "publisher": {"@id": self.person_id}}]
        if content:
            howto = self.howto(url, name, content)
            if howto:
                graph.append(howto)
            graph.append({"@type": "Article", "@id": url + "#article", "headline": tool["h1"][:110], "description": desc,
                          "url": url, "inLanguage": "en-US", "datePublished": published, "dateModified": modified,
                          "wordCount": len(text(content).split()), "articleSection": [text(h) for h in H2_RE.findall(content)],
                          "mainEntityOfPage": {"@id": url + "#webpage"}, "isPartOf": {"@id": url + "#webpage"},
                          "author": {"@id": self.person_id}, "publisher": {"@id": self.person_id},
                          "about": {"@id": main_id}})
        graph.extend(self.faq(url, tool.get("faq")))
        return graph

    def info(self, page, url, trail, published, modified, sitemap_items=None):
        slug = page["slug"]
        if slug == self.author["slug"]:
            node = self.webpage(url, page["h1"], page["meta_description"], published, modified, "ProfilePage",
                                {"mainEntity": {"@id": self.person_id}}, credit=False)
            node["about"] = {"@id": self.person_id}
        else:
            extra = {"mainEntity": {"@id": url + "#tools"}} if slug == "sitemap" else None
            node = self.webpage(url, page["h1"], page["meta_description"], published, modified,
                                PAGE_TYPES.get(slug, "WebPage"), extra, credit=slug in ("about",))
        person = self.person()
        if slug == self.author["slug"]:
            person["mainEntityOfPage"] = {"@id": url + "#webpage"}  # only resolvable on the author's own page
        graph = [self.website(), person, node, self.breadcrumb(url, trail)]
        if slug == "sitemap" and sitemap_items:
            graph.append(self.item_list(url, "tools", "All WebcamTest tools", sitemap_items))
        return graph

    def plain(self, url, trail, name, description):
        return [self.website(), self.person(), self.webpage(url, name, description, credit=False),
                self.breadcrumb(url, trail)]
