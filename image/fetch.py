"""Fetch versioned upstream releases over verified TLS and check upstream hashes."""
import concurrent.futures, hashlib, pathlib, re, time, urllib.request
root=pathlib.Path(__file__).resolve().parent
cache=root/'downloads'; cache.mkdir(exist_ok=True)
apache='https://archive.apache.org/dist/'
maven='https://repo.maven.apache.org/maven2/'
# Large distributions come from digest-pinned official images in Dockerfile.
artifacts=[]
for folder,name in [
 ('io/delta/delta-spark_2.12/3.3.2','delta-spark_2.12-3.3.2'),
 ('io/delta/delta-storage/3.3.2','delta-storage-3.3.2'),
 ('org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/1.10.0','iceberg-spark-runtime-3.5_2.12-1.10.0'),
 ('org/apache/iceberg/iceberg-aws-bundle/1.10.0','iceberg-aws-bundle-1.10.0'),
 ('org/apache/spark/spark-sql-kafka-0-10_2.12/3.5.9','spark-sql-kafka-0-10_2.12-3.5.9'),
 ('org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.5.9','spark-token-provider-kafka-0-10_2.12-3.5.9'),
 ('org/apache/spark/spark-avro_2.12/3.5.9','spark-avro_2.12-3.5.9'),
 ('org/apache/kafka/kafka-clients/3.4.1','kafka-clients-3.4.1'),
 ('org/apache/commons/commons-pool2/2.11.1','commons-pool2-2.11.1'),
 ('com/mysql/mysql-connector-j/8.4.0','mysql-connector-j-8.4.0'),
 ('org/postgresql/postgresql/42.7.8','postgresql-42.7.8'),
 ('org/apache/hadoop/hadoop-aws/3.3.4','hadoop-aws-3.3.4'),
 ('com/amazonaws/aws-java-sdk-bundle/1.12.262','aws-java-sdk-bundle-1.12.262')]:
    artifacts.append((name+'.jar',maven+folder+'/'+name+'.jar','sha1'))
artifacts.append(('lineage/openlineage-spark_2.12-1.53.0.jar', maven+'io/openlineage/openlineage-spark_2.12/1.53.0/openlineage-spark_2.12-1.53.0.jar', 'sha512'))
for folder,name in [('org/apache/hadoop/hadoop-aws/3.3.6','hadoop-aws-3.3.6'),('com/amazonaws/aws-java-sdk-bundle/1.12.367','aws-java-sdk-bundle-1.12.367')]:
    artifacts.append(('hive-s3/'+name+'.jar',maven+folder+'/'+name+'.jar','sha1'))
artifacts.append(('metrics/jmx_prometheus_javaagent-1.0.1.jar', maven+'io/prometheus/jmx/jmx_prometheus_javaagent/1.0.1/jmx_prometheus_javaagent-1.0.1.jar', 'sha1'))
lockfile=root/'artifacts.lock'
locked={}
if lockfile.exists():
    for row in lockfile.read_text().splitlines():
        algorithm,digest,name=row.split(); locked[name]=(algorithm,digest)
def fetch(item):
    name,url,algorithm=item
    if name in locked: algorithm,expected=locked[name]
    else:
        with urllib.request.urlopen(url+'.'+algorithm,timeout=120) as response: checksum=response.read().decode()
        matches=re.findall(r'\b[0-9a-fA-F]{'+str(hashlib.new(algorithm).digest_size*2)+r'}\b',checksum)
        if len(matches)!=1: raise RuntimeError('Ambiguous upstream checksum: '+name)
        expected=matches[0].lower()
    path=cache/name
    path.parent.mkdir(parents=True,exist_ok=True)
    def digest():
        h=hashlib.new(algorithm)
        with path.open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b''): h.update(chunk)
        return h.hexdigest()
    if not path.exists() or digest()!=expected:
        for attempt in range(4):
            try:
                with urllib.request.urlopen(url,timeout=180) as response,path.open('wb') as stream:
                    for chunk in iter(lambda:response.read(1024*1024),b''): stream.write(chunk)
                if digest()!=expected: raise RuntimeError('Checksum mismatch: '+name)
                break
            except Exception:
                if attempt==3: raise
                time.sleep(3)
    print('Verified '+name,flush=True)
    with path.open('rb') as stream: strong_digest=hashlib.file_digest(stream,'sha256').hexdigest()
    return f'sha256 {strong_digest} {name}'
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    results=list(pool.map(fetch,artifacts))
lockfile.write_text('\n'.join(results)+'\n')
