import {startApp} from 'superdesk-core/scripts/index';
import ansaModule from './ansa';

setTimeout(() => {
    startApp(
        [
            {
                id: "ansaIptc",
                load: () => import('./extensions/ansaIptc'),
            },
            {
                id: "imageShortcuts",
                load: () => import('./extensions/imageShortcuts'),
            },
            {
                id: "planning-extension",
                load: () => import('superdesk-planning/client/planning-extension'),
            },
            {
                id: "ansa-archive",
                load: () => import('./extensions/ansa-archive'),
            },
            {
                id: "lineCountInAuthoringHeader",
                load: () => import('./extensions/lineCountInAuthoringHeader'),
            },
        ],
        {},
        {
            countLines: (plainText, lineLength) =>
                plainText
                    .split('\n')
                    .reduce((sum, line) => sum + (line.length > 0 ? Math.ceil(line.length / lineLength) : 1), 0),
        },
    );
});

export default ansaModule;