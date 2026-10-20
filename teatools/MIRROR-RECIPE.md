# Mirroring a TEA-Online tool

The tools are Vue single-page apps. The page HTML is public even for paid tools
(the account only gates the analytics POST to `api/v2/tools`), and all editing
logic is client-side JavaScript. So:

    T=<route>            # e.g. extend/tools/data/initialdeck  (no trailing slash!)
    D=~/teatools/<name>/site; mkdir -p $D; cd $D
    curl -sSL -o page.html "https://www.basededatostea.xyz/$T"
    grep -oE '(href|src)=/[^ >]+\.(js|css|json)' page.html | sed -E 's/^(href|src)=//' | sort -u > assets.txt
    while read -r p; do mkdir -p ".$(dirname "$p")"; curl -sS -o ".$p" "https://www.basededatostea.xyz$p"; done < assets.txt

Then look for lazy chunks the page loads later (`grep -oE 'chunk-[0-9a-f]{8}' js/extend/**/*.js`)
and fetch any that are missing. The tool's own code is `js/extend/tools/<route>.<hash>.js`;
the rest (chunk-vendors, chunk-common, m2.js = Materialize, h.js, saver.js = FileSaver)
is framework.

Reading the minified chunk: `sed 's/},{/},\n{/g; s/;/;\n/g' file.js > pretty.js`, then grep for
`getUint8|setUint8|setUint16|DataView|accepted:|minsize` to find the file reader and the
patch offsets. Every tool so far follows the same shape: a `<X>Reader` component emits a
DataView of the uploaded file, a `get*()` reads bytes at fixed offsets to populate the UI,
`set*()` / `setBytes()` write them back, `saveAs()` downloads the result.

A 404 usually means a typo in the route; the site's real route list is in
`site-index/README.md`.

## Login-gated routes

Some routes (data/disassembler, data/dropUI, media/video, image/editor, image/massive/cards,
process/guardianstars, process/fdfields, process/ritualengine) answer with a 302 to
/extend/user/register unless a session cookie is sent, and the mirror then contains only the
register page (tell-tale: the tool chunk is `register.<hash>.js`). Log in to the site in a
browser, copy the value of the `ts` cookie, and pass it to the mirror script:

    TEA_COOKIE='<ts cookie value>' python3 ~/teatools/mirror.py extend/tools/<route> ...

The token is a session credential: keep it out of files and out of git.
