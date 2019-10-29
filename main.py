#!/usr/bin/env python
# coding: utf-8
# %%

# LTIM time series, 1991 to 2017 Area of Destination or Origin within the UK

# %%
from gssutils import *
scraper = Scraper('https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/internationalmigration/datasets/longterminternationalmigrationareaofdestinationororiginwithintheuktable206')
scraper


# %%
tab = next(t for t in scraper.distributions[0].as_databaker() if t.name == 'Table 2.06')


# %%
cell = tab.filter('Year')
cell.assert_one()
Area = cell.shift(0,2).fill(RIGHT).is_not_blank().is_not_whitespace()
Year = cell.expand(DOWN).filter(lambda x: type(x.value) != str or 'Significant Change?' not in x.value)
Flow = cell.fill(DOWN).one_of(['Inflow', 'Outflow', 'Balance'])


# %%


observations = cell.shift(RIGHT).fill(DOWN).filter('Estimate').expand(RIGHT).filter('Estimate').fill(DOWN).is_not_blank().is_not_whitespace()#.filter(lambda x: type(x.value) != str) 
Str =  tab.filter(contains_string('Significant Change?')).fill(RIGHT).is_not_number()
observations = observations - (tab.excel_ref('A1').expand(DOWN).expand(RIGHT).filter(contains_string('Significant Change')))
original_estimates = tab.filter(contains_string('Original Estimates')).fill(DOWN).is_number()
observations = observations - original_estimates - Str
CI = observations.shift(RIGHT)


# %%


csObs = ConversionSegment(observations, [
    HDim(Year,'Year', DIRECTLY, LEFT),
    HDimConst('Geography','K02000001'),
    HDim(Area,'Area of Destination or Origin', CLOSEST, LEFT),
    HDim(Flow, 'Flow', CLOSEST, ABOVE),
    HDimConst('Measure Type', 'Count'),
    HDimConst('Unit','People (thousands)'),
    HDim(CI,'CI',DIRECTLY,RIGHT),
    HDimConst('Revision', '2011 Census Revision')
])
# savepreviewhtml(csObs)
tidy_revised = csObs.topandas()


# %%


csRevs = ConversionSegment(original_estimates, [
    HDim(Year, 'Year', DIRECTLY, LEFT),
    HDimConst('Geography','K02000001'),
    HDim(Area,'Area of Destination or Origin', CLOSEST, LEFT),
    HDim(Flow, 'Flow', CLOSEST, ABOVE),
    HDimConst('Measure Type', 'Count'),
    HDimConst('Unit','People (thousands)'),
    HDim(original_estimates.shift(RIGHT), 'CI', DIRECTLY, RIGHT),
    HDimConst('Revision', 'Original Estimate')
])
orig_estimates = csRevs.topandas()


# %%
tidy = pd.concat([tidy_revised, orig_estimates], axis=0, join='outer', ignore_index=True, sort=False)


# %%
import numpy as np
# tidy['OBS'].replace('', np.nan, inplace=True)
# tidy.dropna(subset=['OBS'], inplace=True)
# if 'DATAMARKER' in tidy.columns:
#     tidy.drop(columns=['DATAMARKER'], inplace=True)
tidy.rename(columns={'OBS': 'Value'}, inplace=True)
#tidy.rename(columns={'Flow': 'Migration Flow'}, inplace=True)
# tidy['Value'] = tidy['Value'].astype(int)
# tidy['CI'] = tidy['CI'].map(lambda x:'' 
#                             if (x == ':') | (x == 'N/A') 
#                             else int(x[:-2]) if x.endswith('.0') 
#                             else 'ERR')
#tidy['IPS Marker'].unique

# %%
# Metadata at bottom of sheet is being pulled in as well as the observations. Don't fully understand how to solve
# this issue at the moment so have just removed the row for now. LPerryman 
tidy = tidy[tidy.DATAMARKER != 'Statistically Significant Decrease']
#tidy

# %%
#tidy['IPS Marker'] = tidy['DATAMARKER'].map(lambda x: { ':' : 'not-applicable','Statistically Significant Decrease' : 'statistically-significant-decrease'}.get(x, x))

tidy['IPS Marker'] = tidy['DATAMARKER'].map(lambda x: { ':' : 'not-applicable'}.get(x, x))


# %%
tidy['CI'] = tidy['CI'].map(lambda x: { ':' : 'not-applicable',
                                                'N/A' : 'not-applicable'}.get(x, x))


# %%
for col in tidy.columns:
    if col not in ['Value', 'Year', 'CI']:
        tidy[col] = tidy[col].astype('category')
        display(col)
        display(tidy[col].cat.categories)


# %%


tidy['Geography'] = tidy['Geography'].cat.rename_categories({
    'United Kingdom': 'K02000001',
    'England and Wales': 'K04000001'
})
tidy['Flow'] = tidy['Flow'].cat.rename_categories({
    'Balance': 'balance', 
    'Inflow': 'inflow',
    'Outflow': 'outflow'
})

tidy = tidy[['Area of Destination or Origin', 'Year', 'Flow',
              'Measure Type','Value', 'CI','Unit', 'Revision', 'IPS Marker']]


# %%

tidy.head()
# tidy['Year'] = tidy['Year'].apply(lambda x: pd.to_numeric(x, downcast='integer'))


# %%


# tidy['Year'] = tidy['Year'].astype(int)


# %%


from pathlib import Path
destinationFolder = Path('out')
destinationFolder.mkdir(exist_ok=True, parents=True)

tidy.to_csv(destinationFolder / ('observations.csv'), index = False)


# %%


from gssutils.metadata import THEME
scraper.dataset.theme = THEME['population']
scraper.dataset.family = 'migration'

with open(destinationFolder / 'dataset.trig', 'wb') as metadata:
    metadata.write(scraper.generate_trig())
    
csvw = CSVWMetadata('https://gss-cogs.github.io/ref_migration/')
csvw.create(destinationFolder / 'observations.csv', destinationFolder / 'observations.csv-schema.json')


# %%
