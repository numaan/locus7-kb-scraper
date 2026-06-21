# Source coverage

Adding a source = copy `_TEMPLATE.yaml` → `<id>.yaml`, fill in `base_url` + `sitemaps`/`allow`/`deny`
+ `content_selector`, set `license`, and set the **`usage` gate** (`open` / `permitted` / `restricted`
/ `unknown`) after checking the site's ToS, then `kbscraper scrape --source <id>`.

**Only `usage: open` (recognised open licence) or `usage: permitted` (you attested the ToS) sources
are scraped.** Everything else is blocked. The status column below is a *starting* assessment — verify
each before flipping it; non-commercial (NC) and no-derivatives (ND) count as restricted.

**✅ Implemented + open (scrape now):** `postgresql` (PostgreSQL Licence), `kubernetes` (CC-BY-4.0),
`kafka` (Apache-2.0).

**📝 Requested — start URLs + suggested usage** (confirm before enabling):

| id | component | docs start URL | licence | usage (suggested) |
|----|-----------|----------------|---------|-------------------|
| cassandra | Apache Cassandra | https://cassandra.apache.org/doc/latest/ | Apache-2.0 | **open** |
| podman | Podman | https://docs.podman.io/en/latest/ | Apache-2.0 | **open** |
| istio | Istio (service mesh) | https://istio.io/latest/docs/ | Apache-2.0 / CC-BY-4.0 | **open** |
| envoy | Envoy proxy | https://www.envoyproxy.io/docs/envoy/latest/ | Apache-2.0 | **open** |
| docker | Docker | https://docs.docker.com/ | Apache-2.0 (docs repo) | **open** (verify) |
| wso2 | WSO2 API Manager | https://apim.docs.wso2.com/en/latest/ | Apache-2.0 (verify) | **open** (verify) |
| azure | Azure services | https://learn.microsoft.com/en-us/azure/ | often CC-BY-4.0 (MS Learn) | unknown — verify per area; scope tightly |
| apigee | Apigee | https://cloud.google.com/apigee/docs | Google Cloud (often CC-BY-4.0) | unknown — verify |
| couchbase | Couchbase | https://docs.couchbase.com/home/index.html | check ToS | unknown |
| elasticsearch | Elasticsearch | https://www.elastic.co/guide/.../current/index.html | check Elastic licence | unknown |
| openshift | OpenShift | https://docs.openshift.com/container-platform/latest/ | check Red Hat ToS | unknown |
| rancher | Rancher | https://ranchermanager.docs.rancher.com/ | check SUSE ToS | unknown |
| confluent | Confluent (Kafka) | https://docs.confluent.io/platform/current/overview.html | check Confluent ToS | unknown |
| rabbitmq | RabbitMQ | https://www.rabbitmq.com/docs | check Broadcom ToS | unknown |
| kong | Kong Gateway | https://docs.konghq.com/gateway/latest/ | check Kong ToS | unknown |
| nginx | NGINX | https://docs.nginx.com/ | check F5/NGINX ToS | unknown |
| haproxy | HAProxy | https://docs.haproxy.org/ | check HAProxy ToS | unknown |
| oracle | Oracle Database | https://docs.oracle.com/en/database/oracle/oracle-database/ | proprietary | **restricted** |
| mysql | MySQL | https://dev.mysql.com/doc/refman/8.0/en/ | proprietary docs | **restricted** |
| mongodb | MongoDB | https://www.mongodb.com/docs/manual/ | CC-BY-NC-SA (non-commercial) | **restricted** |
| couchbase-ent | Couchbase (proprietary parts) | — | proprietary | **restricted** |
| f5-gtm | F5 BIG-IP DNS (GTM) | https://techdocs.f5.com/ | proprietary | **restricted** |
| f5-ltm | F5 BIG-IP LTM | https://techdocs.f5.com/ | proprietary | **restricted** |
| f5-afm | F5 BIG-IP AFM (firewall) | https://techdocs.f5.com/ | proprietary | **restricted** |
| aws | AWS services | https://docs.aws.amazon.com/ | proprietary | **restricted** |

> ⚠️ This table is guidance, not legal advice. Confirm each source's current Terms of Service / licence
> yourself before setting `usage: open` or `permitted`. Large sites (AWS, Azure, MS Learn) must be
> scoped tightly via `allow` + `max_pages` even when permitted — never crawl them wholesale.
