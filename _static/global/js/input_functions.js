console.debug('pizda ivanna');

function addItem() {
    if (this.items.length < this.maxItems) {
        let fields = window.suffixes.map((suffix, index) => ({
            value: '',
            suffix: suffix,
            regex: new RegExp(window.regex[index], 'i'), // Add regex here
            allowedValues: window.allowedValues[index].map(item => item.toLowerCase())
        }));
        this.items.push({fields: fields});
    }
}

function getFields() {
    let fields = window.suffixes.map((suffix, index) => ({
        value: '',
        suffix: suffix,
        regex: new RegExp(window.regex[index], 'i'),
        allowedValues: window.allowedValues[index].map(item => item.toLowerCase())
    }));
    return fields
}

function checkSingleField(field) {
    const convValue = field.value.toLowerCase().trim()
    const regex = field.regex;
    console.debug(convValue, regex, regex.test(convValue))
    console.debug('*')
    return regex.test(convValue);
    //aValues = field.allowedValues;
    //const inAllowedValues = aValues.length === 0 ? true : aValues.includes(convValue)

    //return (inAllowedValues);
}