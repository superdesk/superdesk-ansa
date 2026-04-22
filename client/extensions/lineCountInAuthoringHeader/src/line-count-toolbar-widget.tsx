import * as React from 'react';

import {IArticle, ISuperdesk} from 'superdesk-api';

export function getLineCountToolbarWidget(superdesk: ISuperdesk) {
    const {gettext, gettextPlural} = superdesk.localization;
    const {getLinesCount, stripHtmlTags} = superdesk.utilities;
    const ATTACH_RETRY_MS = 250;
    const MAX_ATTACH_ATTEMPTS = 20;

    return class LineCountToolbarWidget extends React.PureComponent<
        {entity: IArticle},
        {linesCount: number | null}
    > {
        private observer: MutationObserver | null = null;
        private editorEl: HTMLElement | null = null;
        private attachTimer: number | null = null;
        private attachAttempts = 0;
        private frameId: number | null = null;

        constructor(props: {entity: IArticle}) {
            super(props);
            this.state = {linesCount: computeFromEntity(props.entity)};
        }

        componentDidMount() {
            this.tryAttachObserver();
        }

        componentDidUpdate(prevProps: {entity: IArticle}) {
            if (prevProps.entity === this.props.entity) {
                return;
            }

            const currentEl = document.getElementById('bodyhtml');

            if (currentEl !== this.editorEl) {
                this.teardownObserver();
                this.tryAttachObserver();
            }

            if (this.editorEl == null) {
                const next = computeFromEntity(this.props.entity);
                if (next !== this.state.linesCount) {
                    this.setState({linesCount: next});
                }
            }
        }

        componentWillUnmount() {
            this.teardownObserver();
        }

        private teardownObserver = () => {
            this.observer?.disconnect();
            this.observer = null;
            this.editorEl = null;
            this.attachAttempts = 0;
            if (this.attachTimer != null) {
                window.clearTimeout(this.attachTimer);
                this.attachTimer = null;
            }
            if (this.frameId != null) {
                window.cancelAnimationFrame(this.frameId);
                this.frameId = null;
            }
        };

        private tryAttachObserver = () => {
            const el = document.getElementById('bodyhtml');

            if (el == null) {
                if (this.attachAttempts >= MAX_ATTACH_ATTEMPTS) {
                    this.attachTimer = null;
                    return;
                }
                this.attachAttempts += 1;
                this.attachTimer = window.setTimeout(this.tryAttachObserver, ATTACH_RETRY_MS);
                return;
            }

            this.attachTimer = null;
            this.attachAttempts = 0;
            this.editorEl = el;
            this.observer?.disconnect();
            this.observer = new MutationObserver(this.scheduleRecompute);
            this.observer.observe(el, {
                characterData: true,
                subtree: true,
                childList: true,
            });
            this.recompute();
        };

        private scheduleRecompute = () => {
            if (this.frameId != null) {
                return;
            }

            this.frameId = window.requestAnimationFrame(() => {
                this.frameId = null;
                this.recompute();
            });
        };

        private recompute = () => {
            if (this.editorEl == null) {
                return;
            }

            const blocks = this.editorEl.querySelectorAll('[data-block="true"]');
            const plainText = Array.from(blocks)
                .map((block) => block.textContent ?? '')
                .join('\n');
            const next = getLinesCount(plainText);

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
