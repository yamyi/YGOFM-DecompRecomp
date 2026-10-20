# Hextext / Campaign Editor Studio — deployed source snapshot

Retrieved from <https://www.basededatostea.xyz/extend/tools/hextext> on 2026-10-11. The downloaded editor displays version `V.261005`.

This contains the publicly served browser code, including the editor implementation. It is **not the original development repository**: Vue templates have been compiled into render functions, variable names are minified, and original comments and build configuration are unavailable. The main bundle's `.js.map` URL returned HTTP 404. No original source repository was found in the searches performed.

## Files

- `public/`: original, unmodified HTML and same-origin JavaScript/CSS files referenced by the page, including the three prefetched JavaScript chunks.
- `readable/`: copies of those files, with JavaScript and CSS formatted using Prettier 3.9.10. The HTML is unchanged. Formatting does not recover original variable names or Vue source files.
- `manifest.json`: download URLs, retrieval time, sizes, and SHA-256 hashes for the original files.
- `VALIDATION.txt`: results of hash and JavaScript syntax checks.

Start with [the readable editor bundle](readable/js/extend/tools/hextext.70bd1a20.js). Its original URL is <https://www.basededatostea.xyz/js/extend/tools/hextext.70bd1a20.js>.

## Where to find the logic

Line numbers below refer to the formatted copies in this snapshot.

| Area | File | Starting line |
| --- | --- | ---: |
| Editor UI render function | `readable/js/extend/tools/hextext.70bd1a20.js` | 262 |
| Campaign timeline component | same | 3684 |
| Dialogue command insertion/editing methods | same | 4313 |
| Pointer editor component | same | 5266 |
| Main Hextext component and initial state | same | 5338 |
| Dialogue bytecode interpretation (`texto`) | same | 5398 |
| Character decoding (`trad`, `getSimbol`) | same | 6324 |
| Reading bytes into the editor (`getData`) | same | 6336 |
| Character/hex edits (`conver`, `conver2`) | same | 6371 |
| Writing changes and downloading SLUS | same | 6439 |
| Writing and downloading WA_MRG.MRG | same | 6455 |
| Site API calls and application initialization | same | 6690 |
| Character-set editor (`CharLoader`) | `readable/js/chunk-common.c72cb792.js` | 2623 |
| Character tables (Webpack module `5645`) | same | 8261 |
| Shared SLUS helpers (Webpack module `5e6c`) | same | 8645 |
| File input component | same | 9943 |

The editor initially reads 256 bytes at SLUS offset `1710688` (`0x1A1A60`). The main component operates on browser `DataView` objects and downloads changes through `Blob`/`saveAs`. These are observations of the deployed code, not a compatibility guarantee for other game revisions or mods.

## Scope and limitations

This is a source inspection package, not a verified standalone/offline application. The deployed application includes account initialization, redirects, and site API calls. No account checks or other behavior were modified. Server-side implementation is not included, and the original build system cannot be recovered from these files alone.

Fonts referenced inside stylesheets, images, the web manifest, third-party advertising/analytics scripts, and data retrieved at runtime are not included. No game files are included. The package has been checked for JavaScript syntax and original-file integrity, but editing/saving real game files has not been tested.

The code remains the work of its original authors; this snapshot does not assign a new license.
