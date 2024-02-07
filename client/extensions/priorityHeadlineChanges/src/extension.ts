import {ContentState, EditorState} from 'draft-js';
import {IArticle, IEditor3ValueOperational, IExtension, IExtensionActivationResult} from 'superdesk-api';
import {changeEditorState} from 'superdesk-core/scripts/core/editor3/actions/editor3';
import ng from 'superdesk-core/scripts/core/services/ng';
import {getContentStateFromHtml} from 'superdesk-core/scripts/core/editor3/html/from-html';
import {isEqual} from 'lodash';
import {appConfig} from 'superdesk-core/scripts/appConfig';

const extension: IExtension = {
    id: 'priority-headline-changes',
    activate: () => {
        const result: IExtensionActivationResult = {
            contributions: {
                authoring: {
                    onFieldChange: (fieldId, fieldsData, computeLatestEntity, exposed) => {
                        // acts as previous article here, fieldsData has the actual latest data,
                        // this one has the latest rendered data
                        const prevArticle = computeLatestEntity();
                        let headline = (fieldsData.get('headline') as {store: any; contentState: ContentState})
                            .contentState.getPlainText();
                        const priority: number = fieldsData.get('priority') as number;
                        const genre = fieldsData.get('genre');
                        const prevGenre = prevArticle.genre[0].qcode;

                        if (priority == prevArticle.priority && genre == prevGenre) {
                            return fieldsData;
                        }

                        let updated = false;
                        const hasPlus = headline.includes('+');
                        const flashRight = ' +++ FLASH +++';
                        const flashLeft = '+++ FLASH +++ ';
                        const bulletRight = ' ++';
                        const bulletLeft = '++ ';

                        if (priority === 1) {
                            if (prevArticle.priority !== 1 && !hasPlus) {
                                headline = flashLeft + headline + flashRight;
                            } else if (prevArticle.priority === 2 && hasPlus) {
                                headline = headline.replaceAll(bulletLeft, '').replaceAll(bulletRight, '');
                                headline = flashLeft + headline + flashRight;
                            }

                            updated = true;
                        } else if (priority === 2) {
                            if (prevArticle.priority !== 2 && !hasPlus) {
                                headline = bulletLeft + headline + bulletRight;
                            } else if (prevArticle.priority === 1 && hasPlus) {
                                headline = headline.replaceAll(flashLeft, '').replaceAll(flashRight, '');
                                headline = bulletLeft + headline + bulletRight;
                            }

                            updated = true;
                        } else if (priority !== 2 && (prevArticle.priority == null || prevArticle.priority === 2 || prevArticle.priority === 1) && hasPlus) {
                            headline = headline
                                .replace(flashRight, '')
                                .replace(flashLeft, '')
                                .replace(bulletLeft, '')
                                .replace(bulletRight, '');
                            updated = true;
                        }

                        // set profile by priority SDANSA-446
                        const changeContentProfile = () => {
                            if (priority && prevArticle.priority !== priority) {
                                const priorityToProfileConfig = appConfig?.ansa?.priority_to_profile_mapping ?? {};
                                const profileFromConfig = priorityToProfileConfig[priority];

                                if (
                                    profileFromConfig != null
                                    && prevArticle.profile !== profileFromConfig
                                ) {
                                    exposed.loadContentProfile(profileFromConfig)
                                }
                            }
                        }

                        // only genre qCode is stored in fieldsData
                        const isSelected = (genreQCode: string) => genreQCode === genre;
                        const wasSelected = (genreQCode: string) => prevArticle.genre.find((_genre) => _genre.qcode === genreQCode) != null;

                        if (!isEqual(genre, prevGenre)) {
                            const genres = ng.get('metadata').values.genre.concat();

                            genres.filter((genre: IArticle['genre'][0]) => wasSelected(genre.qcode) && !isSelected(genre.qcode))
                                .forEach((genre: IArticle['genre'][0]) => {
                                    if (headline.startsWith(genre.name)) {
                                        headline = headline.slice(genre.name.length).trim();
                                        updated = true;
                                    }
                                });

                            const DEFAULT_GENRE = 'Article';
                            genres.filter((genre: IArticle['genre'][0]) => isSelected(genre.qcode) && !wasSelected(genre.qcode) && genre.qcode !== DEFAULT_GENRE)
                                .forEach((genre: IArticle['genre'][0]) => {
                                    if (!headline.startsWith(genre.name)) {
                                        headline = genre.name + ' ' + headline;
                                        updated = true;
                                    }
                                });
                        }

                        if (updated) {
                            const {store} = fieldsData.get('headline') as IEditor3ValueOperational;
                            const content = getContentStateFromHtml(headline);
                            const state = store.getState();
                            const editorState = EditorState.push(
                                state.editorState,
                                content,
                                'spellcheck-change',
                            );
                            store.dispatch(changeEditorState(editorState, true, false));
                        }

                        return {
                            fieldsData,
                            executeSideEffects: () => {
                                changeContentProfile();
                            },
                        };
                    }
                }
            },
        };

        return Promise.resolve(result);
    },
};

export default extension;
