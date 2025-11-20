import {ISuperdesk, IExtension, IExtensionActivationResult} from 'superdesk-api';
import {getLineCountToolbarWidget} from './line-count-toolbar-widget';

const extension: IExtension = {
    activate: (superdesk: ISuperdesk) => {
        const result: IExtensionActivationResult = {
            contributions: {
                authoringTopbar2Widgets: [{
                    component: getLineCountToolbarWidget(superdesk),
                    availableOffline: false,
                    priority: 0.1,
                    group: 'end',
                }],
            },
        };

        return Promise.resolve(result);
    },
};

export default extension;
