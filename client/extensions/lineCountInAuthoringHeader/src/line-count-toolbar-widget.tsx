import * as React from 'react';

import {IArticle, ISuperdesk} from 'superdesk-api';

// body_html is lossy: editor3StateToHtml trims empty paragraphs from both ends.
// Read DraftJS blocks from fields_meta to preserve leading empty lines.
function getPlainText(entity: IArticle, stripHtmlTags: (html: string) => string): string | null {
    const blocks = entity.fields_meta?.body_html?.draftjsState?.[0]?.blocks;

    if (blocks != null) {
        return blocks.map((b: {text: string}) => b.text).join('\n');
    }

    return entity.body_html != null ? stripHtmlTags(entity.body_html) : null;
}

export function getLineCountToolbarWidget(superdesk: ISuperdesk) {
    const {gettext, gettextPlural} = superdesk.localization;
    const {getLinesCount, stripHtmlTags} = superdesk.utilities;

    return class LineCountToolbarWidget extends React.PureComponent<{entity: IArticle}> {
        render() {
            const plainText = getPlainText(this.props.entity, stripHtmlTags);

            if (plainText == null) {
                return null;
            }

            const linesCount = getLinesCount(plainText);

            if (linesCount == null) {
                return null;
            }

            return (
                <dl>
                    <dt>{gettext('Line count')}</dt>
                    {' '}
                    <dd>{linesCount} {gettextPlural(linesCount, 'line', 'lines')}</dd>
                </dl>
            );
        }
    }
}
