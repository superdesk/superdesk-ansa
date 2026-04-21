import * as React from 'react';

import {IArticle, ISuperdesk} from 'superdesk-api';

const POLL_INTERVAL_MS = 1000;

export function getLineCountToolbarWidget(superdesk: ISuperdesk) {
    const {gettext, gettextPlural} = superdesk.localization;
    const {getLinesCount, stripHtmlTags} = superdesk.utilities;

    type IProps = {entity: IArticle};
    type IState = {linesCount: number | null};

    return class LineCountToolbarWidget extends React.PureComponent<IProps, IState> {
        private pollTimer: number | null = null;

        constructor(props: IProps) {
            super(props);
            this.state = {linesCount: computeLinesCount(props.entity)};
        }

        componentDidMount() {
            this.pollTimer = window.setInterval(this.tick, POLL_INTERVAL_MS);
        }

        componentWillUnmount() {
            if (this.pollTimer != null) {
                window.clearInterval(this.pollTimer);
            }
        }

        private tick = () => {
            const next = computeLinesCount(this.props.entity);
            if (next !== this.state.linesCount) {
                this.setState({linesCount: next});
            }
        };

        render() {
            const {linesCount} = this.state;

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

    function computeLinesCount(entity: IArticle): number | null {
        if (entity.body_html == null) {
            return null;
        }
        return getLinesCount(stripHtmlTags(entity.body_html));
    }
}
