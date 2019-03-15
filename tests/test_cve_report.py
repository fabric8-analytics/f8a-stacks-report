import json

from unittest import mock
from f8a_report.cve_report import CVEReport

GITHUB_RESPONSE_PRS = """{
  "total_count": 2,
  "incomplete_results": false,
  "items": [
    {
      "url": "https://api.github.com/repos/fabric8-analytics/cvedb/issues/1114",
      "repository_url": "https://api.github.com/repos/fabric8-analytics/cvedb",
      "labels_url": "https://api.github.com/repos/fabric8-analytics/cvedb/issues/1114/labels{/name}",
      "comments_url": "https://api.github.com/repos/fabric8-analytics/cvedb/issues/1114/comments",
      "events_url": "https://api.github.com/repos/fabric8-analytics/cvedb/issues/1114/events",
      "html_url": "https://github.com/fabric8-analytics/cvedb/pull/1114",
      "id": 401761750,
      "node_id": "MDExOlB1bGxSZXF1ZXN0MjQ2NjAyNjQz",
      "number": 1114,
      "title": "[java] Add CVE-2018-1332",
      "user": {
        "login": "msrb",
        "id": 3759039,
        "node_id": "MDQ6VXNlcjM3NTkwMzk=",
        "avatar_url": "https://avatars0.githubusercontent.com/u/3759039?v=4",
        "gravatar_id": "",
        "url": "https://api.github.com/users/msrb",
        "html_url": "https://github.com/msrb",
        "followers_url": "https://api.github.com/users/msrb/followers",
        "following_url": "https://api.github.com/users/msrb/following{/other_user}",
        "gists_url": "https://api.github.com/users/msrb/gists{/gist_id}",
        "starred_url": "https://api.github.com/users/msrb/starred{/owner}{/repo}",
        "subscriptions_url": "https://api.github.com/users/msrb/subscriptions",
        "organizations_url": "https://api.github.com/users/msrb/orgs",
        "repos_url": "https://api.github.com/users/msrb/repos",
        "events_url": "https://api.github.com/users/msrb/events{/privacy}",
        "received_events_url": "https://api.github.com/users/msrb/received_events",
        "type": "User",
        "site_admin": false
      },
      "labels": [

      ],
      "state": "closed",
      "locked": false,
      "assignee": null,
      "assignees": [

      ],
      "milestone": null,
      "comments": 1,
      "created_at": "2019-01-22T13:21:34Z",
      "updated_at": "2019-02-01T03:24:54Z",
      "closed_at": "2019-02-01T03:24:54Z",
      "author_association": "MEMBER",
      "pull_request": {
        "url": "https://api.github.com/repos/fabric8-analytics/cvedb/pulls/1114",
        "html_url": "https://github.com/fabric8-analytics/cvedb/pull/1114",
        "diff_url": "https://github.com/fabric8-analytics/cvedb/pull/1114.diff",
        "patch_url": "https://github.com/fabric8-analytics/cvedb/pull/1114.patch"
      },
      "body": "",
      "score": 13.678318
    },
    {
      "url": "https://api.github.com/repos/fabric8-analytics/cvedb/issues/1113",
      "repository_url": "https://api.github.com/repos/fabric8-analytics/cvedb",
      "labels_url": "https://api.github.com/repos/fabric8-analytics/cvedb/issues/1113/labels{/name}",
      "comments_url": "https://api.github.com/repos/fabric8-analytics/cvedb/issues/1113/comments",
      "events_url": "https://api.github.com/repos/fabric8-analytics/cvedb/issues/1113/events",
      "html_url": "https://github.com/fabric8-analytics/cvedb/pull/1113",
      "id": 401761714,
      "node_id": "MDExOlB1bGxSZXF1ZXN0MjQ2NjAyNjE0",
      "number": 1113,
      "title": "[java] Add CVE-2018-1331",
      "user": {
        "login": "msrb",
        "id": 3759039,
        "node_id": "MDQ6VXNlcjM3NTkwMzk=",
        "avatar_url": "https://avatars0.githubusercontent.com/u/3759039?v=4",
        "gravatar_id": "",
        "url": "https://api.github.com/users/msrb",
        "html_url": "https://github.com/msrb",
        "followers_url": "https://api.github.com/users/msrb/followers",
        "following_url": "https://api.github.com/users/msrb/following{/other_user}",
        "gists_url": "https://api.github.com/users/msrb/gists{/gist_id}",
        "starred_url": "https://api.github.com/users/msrb/starred{/owner}{/repo}",
        "subscriptions_url": "https://api.github.com/users/msrb/subscriptions",
        "organizations_url": "https://api.github.com/users/msrb/orgs",
        "repos_url": "https://api.github.com/users/msrb/repos",
        "events_url": "https://api.github.com/users/msrb/events{/privacy}",
        "received_events_url": "https://api.github.com/users/msrb/received_events",
        "type": "User",
        "site_admin": false
      },
      "labels": [

      ],
      "state": "closed",
      "locked": false,
      "assignee": null,
      "assignees": [

      ],
      "milestone": null,
      "comments": 1,
      "created_at": "2019-01-22T13:21:28Z",
      "updated_at": "2019-02-01T03:24:21Z",
      "closed_at": "2019-02-01T03:24:21Z",
      "author_association": "MEMBER",
      "pull_request": {
        "url": "https://api.github.com/repos/fabric8-analytics/cvedb/pulls/1113",
        "html_url": "https://github.com/fabric8-analytics/cvedb/pull/1113",
        "diff_url": "https://github.com/fabric8-analytics/cvedb/pull/1113.diff",
        "patch_url": "https://github.com/fabric8-analytics/cvedb/pull/1113.patch"
      },
      "body": "",
      "score": 13.678285
    }
  ]
}
"""

GITHUB_RESPONSE_FILES = """[
  {
    "sha": "073fd7f86d69155295c0a3229c88989940ad9d87",
    "filename": "database/java/2018/1331.yaml",
    "status": "added",
    "additions": 23,
    "deletions": 0,
    "changes": 23,
    "blob_url": "https://github.com/fabric8-analytics/cvedb/blob/ed664d9758b932194e2d6441c913b106833a87ce/database/java/2018/1331.yaml",
    "raw_url": "https://github.com/fabric8-analytics/cvedb/raw/ed664d9758b932194e2d6441c913b106833a87ce/database/java/2018/1331.yaml",
    "contents_url": "https://api.github.com/repos/fabric8-analytics/cvedb/contents/database/java/2018/1331.yaml?ref=ed664d9758b932194e2d6441c913b106833a87ce",
    "patch": "@@ -0,0 +1,23 @@\n+---\n+cve: 2018-1331\n+title: CVE in org.apache.storm:storm-core\n+description: >\n+    In Apache Storm 0.10.0 through 0.10.2, 1.0.0 through 1.0.6, 1.1.0 through 1.1.2, and 1.2.0 through 1.2.1, an attacker with access to a secure storm cluster in some cases could execute arbitrary code as a different user.\n+cvss_v2: 6.5\n+references:\n+    - http://storm.apache.org/2018/06/04/storm113-released.html\n+    - http://storm.apache.org/2018/06/04/storm122-released.html\n+    - http://www.openwall.com/lists/oss-security/2018/07/10/4\n+    - http://www.securityfocus.com/bid/104732\n+    - http://www.securitytracker.com/id/1041273\n+affected:\n+    - groupId: org.apache.storm\n+      artifactId: storm-core\n+      version:\n+        - \"<=0.10.2,0.10.0\"\n+        - \"<=1.0.6,1.0.0\"\n+        - \"<=1.1.2,1.1.0\"\n+        - \"<=1.2.1,1.2.0\"\n+      fixedin:\n+        - \"==1.1.3\"\n+        - \">=1.2.2\""
  }
]
"""

gh_request_state = 0


def _mocked_github_request_prs(_url):
    global gh_request_state
    if gh_request_state == 0:
        gh_request_state += 1
        return json.loads(GITHUB_RESPONSE_PRS)
    else:
        return json.loads(GITHUB_RESPONSE_FILES)


@mock.patch('f8a_report.cve_report.github_request', side_effect=_mocked_github_request_prs)
def test_get_list_of_merged_prs(github_request_function):
    report = CVEReport()
    assert {1113, 1114} == set(report.generate_victimsdb('X', 'Y'))
