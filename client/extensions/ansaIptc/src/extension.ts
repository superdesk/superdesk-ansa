import {IExtension, IExtensionActivationResult, ISuperdesk, IArticle, ISubject, IUser} from 'superdesk-api';

const PHOTO_CATEGORIES_ID = 'PhotoCategories';

// convert 20191209 or 2019:12:09 to 2019-12-09
const parseDate = (date: string) => {
    if (date.length === 8) {
        return [date.substr(0, 4), date.substr(4, 2), date.substr(6, 2)].join('-');
    }
    return date.replace(/:/g, '-');
};

// convert IPTC time to HH:MM:SS±HH:MM (timezone is optional; second precision is required)
// handles: 152339+0000 (compact), 15:23:39+0100 and 15:23:39+01:00 (extended)
// also strips milliseconds if present (e.g. 09:07:19.042+02:00 -> 09:07:19+02:00)
const parseTime = (time: string) => {
    const stripped = time.replace(/\.\d+/, '');
    if (/^\d{2}:\d{2}:\d{2}/.test(stripped)) {
        return stripped.replace(/([+-]\d{2})(\d{2})$/, '$1:$2');
    }
    if (/^\d{6}/.test(stripped)) {
        const hhmmss = [stripped.substr(0, 2), stripped.substr(2, 2), stripped.substr(4, 2)].join(':');
        const tz = stripped.substr(6);
        return hhmmss + tz.replace(/^([+-]\d{2})(\d{2})$/, '$1:$2');
    }
    return stripped;
};

const ISO_DATETIME_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$/;
const ISO_DATETIME_NO_TZ_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/;

// Returns Europe/Rome's UTC offset (e.g. "+02:00") for the given local datetime,
// used as a fallback when IPTC metadata omits the timezone — matches the server-side parser.
const getRomeOffset = (isoDatetime: string): string => {
    const [y, m, d] = isoDatetime.slice(0, 10).split('-').map(Number);
    const [hh] = isoDatetime.slice(11).split(':').map(Number);
    const utc = new Date(Date.UTC(y, m - 1, d, hh));
    const tzName = new Intl.DateTimeFormat('en-US', {
        timeZone: 'Europe/Rome',
        timeZoneName: 'longOffset',
    }).formatToParts(utc).find((p) => p.type === 'timeZoneName')?.value ?? '';
    const match = tzName.match(/GMT([+-]\d{2}:\d{2})/);
    return match ? match[1] : '+01:00';
};

// DateCreated may already include the time (e.g. "2026:04:12 09:07:19.042+02:00");
// in that case use its embedded time and ignore the separate TimeCreated value.
const parseDatetime = (date?: string, time?: string): string | null => {
    if (!date) {
        return null;
    }

    const combined = date.match(/^(\S+)[ T](.+)$/);
    const datePart = combined ? combined[1] : date;
    const timePart = combined ? combined[2] : time;

    if (!timePart) {
        return null;
    }

    let result = `${parseDate(datePart)}T${parseTime(timePart)}`;

    if (ISO_DATETIME_NO_TZ_RE.test(result)) {
        result += getRomeOffset(result);
    }

    if (!ISO_DATETIME_RE.test(result)) {
        console.warn(`parseDatetime: "${result}" is not in expected YYYY-MM-DDThh:mm:ss±hh:mm format`);
        return null;
    }

    return result;
};

const extension: IExtension = {
    activate: (superdesk: ISuperdesk) => {
        const result: IExtensionActivationResult = {
            contributions: {
                iptcMapping: (data, item: IArticle) => Promise.all([
                    superdesk.entities.vocabulary.getIptcSubjects(),
                    superdesk.session.getCurrentUser(),
                ]).then(([subjects, user]: [Array<ISubject>, IUser]) => {
                    const categories: Array<ISubject> = superdesk.entities.vocabulary.getVocabulary(PHOTO_CATEGORIES_ID).items;
                    const subjectReference = Array.isArray(data.SubjectReference) ? data.SubjectReference : [data.SubjectReference || ''];
                    const signOff = user.sign_off || user.username;

                    Object.assign(item, {
                        sign_off: signOff,
                        slugline: data.ObjectName,
                        byline: data['By-line'] || [
                            user.first_name,
                            user.last_name,
                        ].filter((value) => value).join(' '),
                        headline: data.Headline,
                        copyrightholder: data.Credit,
                        copyrightnotice: data.CopyrightNotice,
                        usageterms: data.CopyrightNotice,
                        language: data.LanguageIdentifier || 'it',
                        subject: (item.subject || []).concat(
                            subjects.filter((subj) => subjectReference.find((ref) => ref.includes(subj.qcode))),
                            data.Category != null ?
                                categories.filter((cat) => cat.name === data.Category)
                                    .map((cat) => ({name: cat.name, qcode: cat.qcode, scheme: PHOTO_CATEGORIES_ID})) :
                                [],
                        ),
                        extra: {
                            city: data.City,
                            nation: data['Country-PrimaryLocationName'],
                            digitator: data['Writer-Editor'],
                            coauthor: data['By-lineTitle'] || signOff,
                            supplier: data.Source,
                        },
                    });

                    if (item.extra) {
                        const created = parseDatetime(data.DateCreated, data.TimeCreated);
                        const release = parseDatetime(data.ReleaseDate, data.ReleaseTime);

                        if (created && created !== '') {
                            item.extra.DateCreated = created;
                        }

                        if (release) {
                            item.extra.DateRelease = release;
                        }
                    }

                    // generate random id using timestamp + random bits
                    // will be used as filename when ingesting same binary again
                    item.uri = Date.now().toString(36) + Math.random().toString(36).substr(2) + '.jpg';

                    console.debug('iptc', data, item);

                    return item;
                }),
            },
        };

        return Promise.resolve(result);
    },
};

export default extension;
