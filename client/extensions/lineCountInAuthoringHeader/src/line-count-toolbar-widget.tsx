import * as React from 'react';

import {IArticle, ISuperdesk} from 'superdesk-api';

export function getLineCountToolbarWidget(superdesk: ISuperdesk) {
    const {gettext, gettextPlural} = superdesk.localization;
    const {getLinesCount, stripHtmlTags} = superdesk.utilities;

    return class LineCountToolbarWidget extends React.PureComponent<{entity: IArticle}> {
        render() {
            const {entity} = this.props;
            const plainText = getPlainTextForLineCount(entity);

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
    };

    function getPlainTextForLineCount(entity: IArticle): string | null {
        const blocks = entity.fields_meta?.body_html?.draftjsState?.[0]?.blocks;

        if (blocks != null) {
            return blocks.map((b: {text: string}) => b.text).join('\n');
        }

        if (entity.body_html != null) {
            return stripHtmlTags(entity.body_html);
        }

        return null;
    }
}
