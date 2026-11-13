from pipeline.employers import parse_successfactors_rss

RSS = """<?xml version="1.0"?><rss><channel>
<item>
  <title><![CDATA[Tech_Arquitecto/a Cloud Azure (MADRID, ES)]]></title>
  <link>https://jobs.telefonica.com/job/MADRID-Arquitecto/123/</link>
  <pubDate>Thu, 12 Nov 2026 10:00:00 GMT</pubDate>
  <description><![CDATA[<p>Responsabilidades &amp; funciones</p>]]></description>
</item>
<item>
  <title><![CDATA[Security Architect]]></title>
  <link>https://opportunities.vodafone.com/job/456/</link>
  <pubDate>Wed, 11 Nov 2026 10:00:00 GMT</pubDate>
  <description></description>
</item>
</channel></rss>"""


def test_parse_successfactors_rss():
    items = list(parse_successfactors_rss(RSS))
    assert len(items) == 2
    first, second = items
    assert first["title"] == "Tech_Arquitecto/a Cloud Azure"
    assert first["location"] == "MADRID, ES"
    assert first["id"] == first["url"] == "https://jobs.telefonica.com/job/MADRID-Arquitecto/123/"
    assert first["text"] == "<p>Responsabilidades & funciones</p>"
    assert second["title"] == "Security Architect" and second["location"] is None
