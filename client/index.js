import {startApp} from 'superdesk-core/scripts/index';
import ansaModule from './ansa';

setTimeout(() => {
    startApp(
        [
            {
                id: 'helloWorld',
                load: () => import('./extensions/helloWorld'),
            },
        ],
        {}
    )
});

export default ansaModule;
