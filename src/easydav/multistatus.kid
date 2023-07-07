<?xml version="1.0" encoding="utf-8" ?> 
<?python import kid.parser ?>
<D:multistatus xmlns:D="DAV:" xmlns:py="http://purl.org/kid/ns#"> 
    <D:response py:for="real_url, propstats in result_files">
        <D:href py:content="real_url" />
        <D:propstat py:for="status, props in propstats.items()">
            <D:prop>
                <!-- !A small trick to generate variable tag names in kid. -->
                <element py:for="prop, value in props" py:strip="">
                    <?python
                        if isinstance(value, basestring):
                            value  = [(kid.parser.TEXT, value)]
                        else:
                            value = list(value)
                    ?>
                    <element py:replace="kid.parser.ElementStream(
                        [(kid.parser.START, kid.Element(prop))]
                        + value
                        + [(kid.parser.END, kid.Element(prop))])" />
                </element>
            </D:prop>
            <D:status>HTTP/1.1 ${status}</D:status>
            <D:error py:if="hasattr(status, 'body')"
                     py:content="status.body" />
        </D:propstat>
    </D:response>
</D:multistatus> 

