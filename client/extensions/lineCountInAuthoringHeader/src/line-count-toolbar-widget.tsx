import * as React from 'react';

import {IArticle, ISuperdesk} from 'superdesk-api';

export function getLineCountToolbarWidget(superdesk: ISuperdesk) {
    const {gettext, gettextPlural} = superdesk.localization;
    const {getLinesCount, stripHtmlTags} = superdesk.utilities;

    return class LineCountToolbarWidget extends React.PureComponent<{entity: IArticle}> {
        render() {
            const {entity} = this.props;
            const blocks = entity.fields_meta?.body_html?.draftjsState?.[0]?.blocks;
            const text = blocks != null
                ? blocks.map((b: {text: string}) => b.text).join('\n')
                : entity.body_html != null ? stripHtmlTags(entity.body_html) : null;

            if (text == null) {
                return null;
            }

            const linesCount = getLinesCount(text);

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
