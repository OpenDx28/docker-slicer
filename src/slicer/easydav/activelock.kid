<?xml version="1.0" encoding="utf-8" ?>
<?python import urlparse ?>
<D:prop xmlns:D="DAV:" xmlns:py="http://purl.org/kid/ns#" py:strip="part_only"> 
    <D:lockdiscovery py:strip="part_only">
        <D:activelock > 
            <D:locktype><D:write/></D:locktype> 
            <D:lockscope>
                <D:exclusive py:if="not lock.shared" />
                <D:shared py:if="lock.shared" />
            </D:lockscope> 
            <D:depth py:if="lock.infinite_depth">infinity</D:depth>
            <D:depth py:if="not lock.infinite_depth">0</D:depth> 
            <D:owner py:replace="XML(lock.owner)"></D:owner> 
            <D:timeout>Second-${str(lock.seconds_until_timeout())}</D:timeout>
            <D:locktoken>
                <D:href>${lock.urn}</D:href>
            </D:locktoken> 
            <D:lockroot> 
                <D:href>${urlparse.urljoin(reqinfo.root_url, lock.path)}</D:href>
            </D:lockroot> 
        </D:activelock>
    </D:lockdiscovery>
</D:prop>
