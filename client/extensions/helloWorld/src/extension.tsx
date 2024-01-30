/* eslint-disable react/react-in-jsx-scope */
/* eslint-disable react/no-multi-comp */
/* eslint-disable react/display-name */
import {IExtensionActivationResult} from 'superdesk-api';
import {superdesk} from './superdesk';
import {SemanticsView} from './semantics-view';
import React from 'react';

const {gettext} = superdesk.localization;

const getSemanticsWidgetLabel = () => gettext('Hello World');

// export function refreshAnalysis($scope, api, $rootScope, save) {
//     return api.save('analysis', {
//         lang: $scope.item.language === 'en' ? 'ENG' : 'ITA',
//         title: $scope.item.headline || '',
//         text: [
//             text($scope.item.abstract),
//             text($scope.item.body_html),
//             $scope.item.description_text || '',
//         ].join('\n'),
//         abstract: '',
//     }).then((result) => {
//         saveSemantics($scope, result, save);
//         $rootScope.$broadcast('semantics:update', result.semantics);
//         return result.semantics;
//     });
// }

// export function saveSemantics($scope, result, save) {
//     $scope.item.semantics = result.semantics;

//     if (result.place && isEmpty($scope.item.place)) {
//         $scope.item.place = result.place;
//     }

//     if (!isEmpty(result.subject)) {
//         const subjects = $scope.item.subject || [];

//         $scope.item.subject = subjects.concat(
//             result.subject.filter(
//                 (subject) => !subjects.find(
//                     (selectedSubject) => (
//                         selectedSubject.qcode === subject.qcode &&
//                         (selectedSubject.scheme === subject.scheme || (
//                             selectedSubject.scheme == null && subject.scheme == null
//                         ))
//                     )
//                 ) && (subject.scheme !== 'products' || $scope.item.type === 'text')
//             )
//         );
//     }

//     if (result.slugline && isEmpty($scope.item.slugline)) {
//         $scope.item.slugline = result.slugline;
//     }

//     if (result.keywords && isEmpty($scope.item.keywords)) {
//         $scope.item.keywords = result.keywords;
//     }

//     // Function is used in Related items and Semantics widget both.
//     // In the Related items widget, we don't modify semantics data, we only need it for
//     // further processing. Thus we don't need to save it on the article.
//     if (save) {
//         $scope.save();
//     }
// }

const extension = {
    id: 'helloWorld',
    activate: () => {

        // let init = () => {
        //     if ($scope.item.semantics) {
        //         this.data = angular.extend({}, $scope.item.semantics);
        //     } else {
        //         refreshAnalysis($scope, api, $rootScope, true).then((result) => {
        //             this.data = result;
        //         });
        //     }
        // };

        // this.remove = (term, category) => {
        //     this.data[category] = without(this.data[category], term);
        //     saveSemantics($scope, {semantics: this.data});
        //     broadcast(this.data);
        // };

        // function broadcast(semantics) {
        //     $rootScope.$broadcast('semantics:update', semantics);
        // }

        // init();

        const result: IExtensionActivationResult = {
            contributions: {
                authoringSideWidgets: [
                    {
                        _id: 'helloWorld',
                        label: getSemanticsWidgetLabel(),
                        component: SemanticsView,
                        order: 5,
                        icon: 'dashboard',
                    },
                ],
            }
        };

        return Promise.resolve(result);
    },

};

export default extension;
