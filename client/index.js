import {startApp} from 'superdesk-core/scripts/index';
import ansaModule from './ansa';

setTimeout(() => startApp(
    [],
    {},
    {
        countLines: (plainText, lineLength) =>
            plainText
                .split('\n')
                .reduce((sum, line) => sum + (line.length > 0 ? Math.ceil(line.length / lineLength) : 1), 0),
    },
));

export default ansaModule;
