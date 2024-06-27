var currentCultureSymbol = jQuery("#currentCulture").val();
var financialDecimalPlaces = jQuery('#FinancialDecimalPlaces').val();
var financialCurrencySymbol = jQuery('#CurrencySymbol').val();

var financial_decimal_separator = jQuery('#currentCultureDecimalPoint').val();
var financial_thousands_separator = ',';
if (financial_decimal_separator == ',')
    financial_thousands_separator = '.';

var financial_prefix = '';
var financial_suffix = '';
if (currentCultureSymbol == 'en-US' || currentCultureSymbol == 'en-GB') {
    financial_prefix = jQuery('#CurrencySymbol').val();
} else {
    financial_suffix = jQuery('#CurrencySymbol').val();
}

var financialMoneyFormat = wNumb({
    prefix: financial_prefix,
    decimals: financialDecimalPlaces,
    mark: financial_decimal_separator,
    thousand: financial_thousands_separator,
    suffix: financial_suffix
});

var financialNumberFormat = wNumb({
    prefix: '',
    decimals: financialDecimalPlaces,
    mark: financial_decimal_separator,
    thousand: financial_thousands_separator,
    suffix: ''
});