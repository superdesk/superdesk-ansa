import * as React from 'react';

import {IArticle, ISuperdesk} from 'superdesk-api';

export function getLineCountToolbarWidget(superdesk: ISuperdesk) {
    const {gettext, gettextPlural} = superdesk.localization;
    const {getLinesCount, stripHtmlTags} = superdesk.utilities;

    return class LineCountToolbarWidget extends React.PureComponent<
        {entity: IArticle},
        {linesCount: number | null}
    > {
        private observer: MutationObserver | null = null;
        private editorEl: HTMLElement | null = null;
        private attachTimer: number | null = null;

        constructor(props: {entity: IArticle}) {
            super(props);
            this.state = {linesCount: computeFromEntity(props.entity)};
        }

        componentDidMount() {
            this.tryAttachObserver();
        }

        componentDidUpdate(prevProps: {entity: IArticle}) {
            if (this.editorEl == null && prevProps.entity !== this.props.entity) {
                const next = computeFromEntity(this.props.entity);
                if (next !== this.state.linesCount) {
                    this.setState({linesCount: next});
                }
            }
        }

        componentWillUnmount() {
            this.observer?.disconnect();
            if (this.attachTimer != null) {
                window.clearTimeout(this.attachTimer);
            }
        }

        private tryAttachObserver = () => {
            const el = document.getElementById('bodyhtml');

            if (el == null) {
                this.attachTimer = window.setTimeout(this.tryAttachObserver, 250);
                return;
            }

            this.editorEl = el;
            this.observer = new MutationObserver(this.recompute);
            this.observer.observe(el, {
                characterData: true,
                subtree: true,
                childList: true,
            });
            this.recompute();
        };

        private recompute = () => {
            if (this.editorEl == null) {
                return;
            }
            const next = getLinesCount(this.editorEl.innerText ?? '');
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

    function computeFromEntity(entity: IArticle): number | null {
        const blocks = entity.fields_meta?.body_html?.draftjsState?.[0]?.blocks;

        if (blocks != null) {
            return getLinesCount(blocks.map((b: {text: string}) => b.text).join('\n'));
        }

        if (entity.body_html != null) {
            return getLinesCount(stripHtmlTags(entity.body_html));
        }

        return null;
    }
}
