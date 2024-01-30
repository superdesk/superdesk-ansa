import React, {ReactNode} from 'react'
import {superdesk} from '../src/superdesk';
import {without} from 'lodash';
import {IExtensionActivationResult} from 'superdesk-api';
// import {Tag} from 'superdesk-ui-framework/react'
const {gettext} = superdesk.localization;
const {AuthoringWidgetLayout, AuthoringWidgetHeading} = superdesk.components;
const {httpRequestJsonLocal} = superdesk;

interface IState {
    semantics: any | null;
    loading: true | false;
    error: string | null;
    other: any | null,
}

type IProps = React.ComponentProps<IExtensionActivationResult['contributions']['authoringSideWidgets'][0]['component']>;

export class SemanticsView extends React.PureComponent<any, IState> {
    constructor(props) {
        super(props);

        console.log(props)
        this.state = {
            other: null,
            semantics: null,
            loading: true,
            error: null,
        }
    }
    componentDidMount(): void {
        const {language, headline, abstract, body_html, description_text} = this.props.article;
        console.log(this.props.article.semantics)
        httpRequestJsonLocal({
            method: 'POST',
            path: '/analysis',
            payload: {
                lang: language === 'en' ? 'ENG' : 'ITA',
                title: headline ?? '',
                text: [
                    abstract,
                    body_html,
                    description_text ?? '',
                ].join('\n'),
                abstract: ''
            }
        }).then((result: any) => {
            this.setState({
                loading: false,
                semantics: result.semantics.data,
                other: result.semantics,
                // result.subject
                // result.place
                // result.slugline
                // result.keywords
            })
        }).catch((error) => {
            this.setState({
                loading: false,
                semantics: this.props.article.semantics,
                error: JSON.stringify(error),
            })
        })
    }
    render(): ReactNode {
       return (
        this.state.loading ? <div>loading</div> :
            <AuthoringWidgetLayout
                header={(
                    <>
                    {this.state.error}
                        <AuthoringWidgetHeading
                            widgetName={this.props.getLabel?.() ?? 'Hello world'}
                            editMode={false}
                        >
                            <button
                                // ng-disabled="item.state === 'published'"
                                className="btn btn--icon-only-circle btn--hollow btn--primary"
                                // ng-click="semantics.refresh()"
                                sd-tooltip={gettext('Refresh')}
                            >
                                <i className="icon-repeat" />
                            </button>
                        </AuthoringWidgetHeading>
                    </>
                )}
                body={(
                    <dl ng-if="semantics.data" className="tag-list">
                        <dt className="tag-list__header">{gettext('IPTC Domains')}</dt>
                        <dd className="tag-label">
                            {(this.state.semantics?.iptcDomains ?? []).map((domain) => (
                                <button
                                    // text={domain}
                                    onClick={() => {
                                        this.setState({
                                            semantics: {
                                                ...this.state.semantics,
                                                iptcDomains: without(this.state.semantics.iptcDomains, domain)
                                            }
                                        })
                                    }}
                                >
                                    {domain}
                                </button>
                            ))}
                        </dd>

                    {/* <dt className="tag-list__header" translate>Products</dt>
                    <dd ng-repeat="product in semantics.data.subjects" className="tag-label">
                        {{ product }}
                        <button className="tag-label__remove" ng-click="semantics.remove(product, 'subjects')"><i className="icon-close-small"></i></button>
                    </dd>

                    <dt className="tag-list__header" translate>News Domains</dt>
                    <dd ng-repeat="domain in semantics.data.newsDomains" className="tag-label">
                        {{ domain }}
                        <button className="tag-label__remove" ng-click="semantics.remove(domain, 'newsDomains')"><i className="icon-close-small"></i></button>
                    </dd>

                    <dt className="tag-list__header" translate>Person</dt>
                    <dd ng-repeat="person in semantics.data.persons" className="tag-label">
                        {{ person }}
                        <button className="tag-label__remove" ng-click="semantics.remove(person, 'persons')"><i className="icon-close-small"></i></button>
                    </dd>

                    <dt className="tag-list__header" translate>Place</dt>
                    <dd ng-repeat="place in semantics.data.places" className="tag-label">
                        {{ place }}
                        <button className="tag-label__remove" ng-click="semantics.remove(place, 'places')"><i className="icon-close-small"></i></button>
                    </dd>

                    <dt className="tag-list__header" translate>Organization</dt>
                    <dd ng-repeat="org in semantics.data.organizations" className="tag-label">
                        {{ org }}
                        <button className="tag-label__remove" ng-click="semantics.remove(org, 'organizations')"><i className="icon-close-small"></i></button>
                    </dd>

                    <dt className="tag-list__header" translate>Main Groups</dt>
                    <dd ng-repeat="group in semantics.data.mainGroups" className="tag-label">
                        {{ group }}
                        <button className="tag-label__remove" ng-click="semantics.remove(group, 'mainGroups')"><i className="icon-close-small"></i></button>
                    </dd>

                    <dt className="tag-list__header" translate>Main Lemmas</dt>
                    <dd ng-repeat="lemma in semantics.data.mainLemmas" className="tag-label">
                        {{ lemma }}
                        <button className="tag-label__remove" ng-click="semantics.remove(lemma, 'mainLemmas')"><i className="icon-close-small"></i></button>
                    </dd>

                    <dt className="tag-list__header" translate>IPTC Codes</dt>
                    <dd ng-repeat="code in semantics.data.iptcCodes" className="tag-label">
                        {{ code }}
                        <button className="tag-label__remove" ng-click="semantics.remove(code, 'iptcCodes')"><i className="icon-close-small"></i></button>
                    </dd>

                    <dt className="tag-list__header" translate>Main sentence</dt>
                    <dd className="tag-list__text-block"><p>{{ semantics.data.mainSenteces[0] }}</p></dd>
                    <dd className="tag-list__text-block"><p>{{ semantics.data.mainSenteces[1] }}</p></dd>
                    <dd className="tag-list__text-block"><p>{{ semantics.data.mainSenteces[2] }}</p></dd> */}
                    </dl>
                )}
            />
        )
    }
}
