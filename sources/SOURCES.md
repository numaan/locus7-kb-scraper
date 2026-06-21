# Source coverage

Adding a source = copy `_TEMPLATE.yaml` → `<id>.yaml`, fill in `base_url` + `sitemaps`/`allow`/`deny`
+ `content_selector`, set `license` after checking the site's ToS, then `kbscraper scrape --source <id>`.

**✅ Implemented (working configs):** `postgresql`, `kubernetes`, `kafka`.

**📝 Requested — ready to configure** (start URLs + licence notes; verify ToS/robots before enabling):

| id | component | docs start URL | licence note |
|----|-----------|----------------|--------------|
| oracle | Oracle Database | https://docs.oracle.com/en/database/oracle/oracle-database/ | proprietary — check Oracle ToS |
| mysql | MySQL | https://dev.mysql.com/doc/refman/8.0/en/ | proprietary docs — check ToS |
| mongodb | MongoDB | https://www.mongodb.com/docs/manual/ | CC-BY-NC-SA — non-commercial |
| cassandra | Apache Cassandra | https://cassandra.apache.org/doc/latest/ | Apache-2.0 |
| couchbase | Couchbase | https://docs.couchbase.com/home/index.html | check Couchbase ToS |
| elasticsearch | Elasticsearch | https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html | check Elastic licence |
| openshift | OpenShift | https://docs.openshift.com/container-platform/latest/welcome/index.html | check Red Hat ToS |
| rancher | Rancher | https://ranchermanager.docs.rancher.com/ | check SUSE ToS |
| docker | Docker | https://docs.docker.com/ | check Docker ToS (has sitemap) |
| podman | Podman | https://docs.podman.io/en/latest/ | Apache-2.0 |
| f5-gtm | F5 BIG-IP DNS (GTM) | https://techdocs.f5.com/ | proprietary — check F5 ToS |
| f5-ltm | F5 BIG-IP LTM | https://techdocs.f5.com/ | proprietary — check F5 ToS |
| f5-afm | F5 BIG-IP AFM (firewall) | https://techdocs.f5.com/ | proprietary — check F5 ToS |
| aws | AWS services | https://docs.aws.amazon.com/ | check AWS ToS (huge — scope `allow`) |
| azure | Azure services | https://learn.microsoft.com/en-us/azure/ | check MS Learn ToS (has sitemaps) |
| confluent | Confluent (Kafka) | https://docs.confluent.io/platform/current/overview.html | check Confluent ToS |
| rabbitmq | RabbitMQ | https://www.rabbitmq.com/docs | check VMware/Broadcom ToS |
| istio | Istio (service mesh) | https://istio.io/latest/docs/ | Apache-2.0 (has sitemap) |
| kong | Kong Gateway | https://docs.konghq.com/gateway/latest/ | check Kong ToS |
| wso2 | WSO2 API Manager | https://apim.docs.wso2.com/en/latest/ | Apache-2.0 docs (verify) |
| apigee | Apigee | https://cloud.google.com/apigee/docs | check Google Cloud ToS |
| nginx | NGINX (gateway/ingress) | https://docs.nginx.com/ | check F5/NGINX ToS |
| envoy | Envoy proxy | https://www.envoyproxy.io/docs/envoy/latest/ | Apache-2.0 |
| haproxy | HAProxy | https://docs.haproxy.org/ | check HAProxy ToS |

> ⚠️ Licences vary widely. Some docs are permissively licensed (Apache-2.0, CC-BY); others are
> proprietary or non-commercial. Scraping + storing text in a vector DB is **your** responsibility to
> clear per source. Large sites (AWS, Azure, Microsoft Learn) must be scoped tightly via `allow`/
> `max_pages` — do not crawl them wholesale.
