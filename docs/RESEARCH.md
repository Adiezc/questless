# Research evidence behind roadmap milestones

Some milestones make claims about the real world: what a tax does, why newcomers fall behind, which
policies help. This file collects the peer-reviewed evidence behind those claims, so that the
game's levers, defaults and lessons (M26) rest on findings rather than intuition, and so the
"what the model leaves out" notes can say where the game is simpler than the research.

**How the evidence was gathered:** relevance-ranked searches of peer-reviewed literature with
[Consensus](https://consensus.app), followed by bibliographic metadata from
[Crossref](https://www.crossref.org). Findings are taken from each paper's abstract, not its full
text. Where a working paper has since been published, the published version is cited; its exact
figures may differ slightly from the working paper's. Check the paper before relying on a number.

**Adding research for a milestone:** add a section named after the milestone with the findings by
lever, what the evidence does not settle, the gaps not yet searched, and an APA 7 reference list
with DOI links. Link to it from the milestone in [ROADMAP.md](ROADMAP.md).

## Contents

- [M58: fairness for late joiners](#m58-fairness-for-late-joiners) (searched 2026-10-23)

## M58: fairness for late joiners

The question: in a world that has run for a decade, how far ahead are the players who were there
first, why, and which levers narrow the gap without driving veterans away?

### What the evidence changes in the design

1. **The ledger removes the biggest weakness of real wealth taxes.** Real taxpayers misreport what
   the authorities can't cross-check, and exploit exemptions and liability caps (Londoño-Vélez &
   Ávila-Mahecha, 2024; Mas-Montserrat et al., 2025; Seim, 2017). Every Questless holding is on
   the ledger, so misreporting is impossible by construction. What remains is avoidance through
   exemptions and migration (Brülhart et al., 2022; Iacono & Smedsvik, 2026). So M58's levy has
   **no exemptions and no liability cap**, and its avoidance is measured as migration between
   regions (M34).
2. **Returns differ by wealth, and land and housing drive most of the gap.** The long-run link
   between r − g and wealth concentration runs mainly through housing returns (Jakurti, 2025), and
   returns rise with position in the wealth distribution (Iacono & Palagi, 2023). Land and mining
   claims therefore matter more than a flat levy on coin.
3. **Early exposure and social contact matter most.** Gains from a better environment rise with
   years of exposure and appear for the young, not for adults (Chetty et al., 2016; Chetty &
   Hendren, 2018; Ludwig et al., 2013), and contact with better-off peers drives them (Chetty et
   al., 2026). Levers should act on a newcomer's first days and on who they play alongside.

### Findings by lever

#### Measuring the gap

| Finding | Design consequence |
|---|---|
| Across 16 countries since 1870, a 1-point wider r − g gap goes with a 3.7% rise in the top 1% wealth share; housing returns are the main long-run driver; repealing net wealth taxes amplifies the effect (Jakurti, 2025). | Report capital income against wage income, split by asset type, in every M58 run. |
| r − g explains over half the rise in US wealth inequality since the late 1970s (Strauss & Ventosa-Santaularia, 2023). | Treat r − g as a measured series, not a parameter. |
| Piketty argues r − g amplifies the inequality that a given mix of shocks produces, and is not the only driver (Piketty, 2015). | The report should show r − g alongside shocks, not as the sole explanation. |
| In Norwegian administrative data, returns rise with position in the wealth distribution (Iacono & Palagi, 2023). | Give richer holders access to higher-return assets, as in reality, and measure the effect. |
| Higher inequality goes with lower intergenerational mobility, the "Great Gatsby curve" (Durlauf et al., 2022), with education a key mechanism (Jerrim & Macmillan, 2015). | Plot inequality against mobility across seeds and regions; the game can test whether its own levers move a world along the curve. |
| Mentor–mentee pairs in academia show their own Great Gatsby curve: impact persists across academic generations (Sun et al., 2024). | Paid mentoring can transmit advantage as well as reduce it. Measure mobility with mentors on and off. |

#### Progressive levy

| Finding | Design consequence |
|---|---|
| Swedish wealth-tax responses reflect evasion and avoidance rather than less saving; about a third came from under-reported assets (Seim, 2017). | Under-reporting is impossible on the ledger, so the in-game levy should show a smaller response than real taxes, which is itself a lesson. |
| A 1-point lower cantonal wealth tax raised reported wealth by at least 43% after 6 years, with about a quarter from taxpayers moving (Brülhart et al., 2022). | Migration between regions (M34) is the main avoidance channel to model. |
| Spanish taxpayers moved into exempt assets, and the cap on total liability accounted for most of the revenue lost (Mas-Montserrat et al., 2025). | No exemptions and no liability cap. |
| Colombian taxpayers misreported what authorities couldn't verify and hid assets offshore (Londoño-Vélez & Ávila-Mahecha, 2024). | The ledger plays the role of complete third-party reporting. |
| After a local wealth-tax cut in Norway, migration of wealthy taxpayers dominated, but there was no national exodus (Iacono & Smedsvik, 2026). | Expect regional moves, not players quitting the world; measure both. |

#### Land value tax on claims

| Finding | Design consequence |
|---|---|
| Widely seen as efficient but rarely implemented, because it needs a complete land registry and valuations that separate land from buildings (Hughes et al., 2020). | The game has both by construction: claims are registered and their unworked value is measurable. |
| US counties that tax land more heavily than buildings grow faster in density, businesses and earnings (Murphy & Seegert, 2026). | Measure claim use, output and new businesses with the tax on and off. |
| The effect on sprawl is contested (Skaburskis, 1995), and Estonia's land-only tax had mixed results (Wenner, 2018). | The lesson presents the debate, not a verdict. |

#### Resource dividend

| Finding | Design consequence |
|---|---|
| Alaska's dividend had no effect on employment and raised part-time work by 1.8 points (Jones & Marinescu, 2022). | A mine-royalty dividend paid equally to every character; measure participation and hours. |
| A $1,000 larger dividend shrinks the labour market by 0.7% a year, through both supply and demand (Bibler et al., 2022). | Expect small, mixed effects; report them honestly. |
| New businesses got an early boost that faded over time (Feinberg & Kuehn, 2020). | Track NPC and player startups over years, not weeks. |

#### Entry barriers (guild fees and licences)

| Finding | Design consequence |
|---|---|
| Licensing raises wages and hours but reduces employment, with a welfare loss of about 12% of occupational surplus (Kleiner & Soltas, 2023). | Guild entry fees and quotas are knobs whose cost the report measures. |
| Licensing reduces labour supply by 17–27% (Blair & Chung, 2019). | Measure how many players enter each profession. |
| A contrary study finds licensing does not raise wages and can ease entry for disadvantaged groups (Redbird, 2017). | Give licences a real quality signal, not only a cost, so the trade-off exists. |
| Stricter scope-of-practice rules raised prices by 3–16% with no measurable quality gain (Kleiner et al., 2016). | Measure quality as well as price when a guild restricts entry. |

#### Residents voting on building permits

| Finding | Design consequence |
|---|---|
| Credible studies associate restrictions with higher prices, and incumbents who control planning can make regions less affordable, but strong causal proof is missing (Quigley & Rosenthal, 2005). | Residents (M32) vote on permits in growing towns (M35); newcomers can't vote at first. |
| In San Francisco, Los Angeles and Seattle, the "zoning tax" on land at least equals typical household income (Gyourko & Krimmel, 2021). | Measure the price premium that permits create. |
| Without Auckland's upzoning, dwelling prices would be an estimated 15–27% higher (Greenaway-McGrevy, 2025). | A reform scenario: loosen permits and compare. |
| Loosening rules adds about 0.8% to supply within a few years, mostly at the higher end (Stacy et al., 2023). | Expect slow effects; run the scenario long enough. |

#### Where newcomers start

| Finding | Design consequence |
|---|---|
| Children who moved to lower-poverty areas before age 13 earned about 31% more as young adults; older children did not gain (Chetty et al., 2016). | Help newcomers early; it is too late once they are established. |
| Each year of childhood exposure to a better area improves outcomes by about 4% (Chetty & Hendren, 2018). | The effect grows with time spent; measure by days played in each region. |
| Moving improved adults' health and well-being but not their economic outcomes (Ludwig et al., 2013). | Relocation help won't close the gap for established players. |
| Gains came largely from social interaction with better-off peers (Chetty et al., 2026). | Apprentice and mixed newcomer–veteran group contracts are the main lever. |

#### Starting grants

| Finding | Design consequence |
|---|---|
| Simulated universal baby bonds, assuming no behavioural response, cut the median Black–white wealth gap among young adults from 16× to 1.4× and the top decile's share from 72% to 65% (Zewde, 2019). | A starting grant for each new character, funded by inheritance tax once dynasties exist. |
| Universal, automatic child development accounts have positive effects on parents and children (Huang et al., 2021). | Make the grant automatic, not something to apply for. |
| Targeting low-income families maximises the reduction in gaps; universal accounts may reduce some families' private saving (Glavan, 2024). | Grade the grant inversely to family wealth, and measure saving responses. |

### What the evidence does not settle

- How general r − g is as a driver of inequality (Piketty, 2015; Strauss & Ventosa-Santaularia,
  2023).
- Whether licensing mainly blocks entry or signals quality (Kleiner & Soltas, 2023; Redbird,
  2017).
- How large and how causal the price effects of land-use regulation are (Quigley & Rosenthal,
  2005).
- Whether land value taxes reduce sprawl (Skaburskis, 1995; Wenner, 2018).

The game can't resolve these debates, but it can show each mechanism working in isolation, which
is what M26 lessons are for.

### Gaps not yet searched

- Craft guilds as barriers to entry (for example Ogilvie's work on European guilds).
- Apprenticeship systems and youth employment.
- Cumulative advantage (the Matthew effect) and recency-weighted reputation.
- Catch-up mechanics and seasonal resets in other MMOs.

### References

Bibler, A., Guettabi, M., & Reimer, M. N. (2022). Universal cash transfers and labor market
outcomes. *Journal of Policy Analysis and Management, 42*(1), 198–224.
https://doi.org/10.1002/pam.22455

Blair, P. Q., & Chung, B. W. (2019). How much of barrier to entry is occupational licensing?
*British Journal of Industrial Relations, 57*(4), 919–943. https://doi.org/10.1111/bjir.12470

Brülhart, M., Gruber, J., Krapf, M., & Schmidheiny, K. (2022). Behavioral responses to wealth
taxes: Evidence from Switzerland. *American Economic Journal: Economic Policy, 14*(4), 111–150.
https://doi.org/10.1257/pol.20200258

Chetty, R., Diamond, R., Foster, T., Katz, L., Porter, S., Staiger, M., & Tach, L. (2026).
*Creating high-opportunity neighborhoods: Evidence from the HOPE VI program* (NBER Working Paper
No. 34720). National Bureau of Economic Research. https://doi.org/10.3386/w34720

Chetty, R., & Hendren, N. (2018). The impacts of neighborhoods on intergenerational mobility I:
Childhood exposure effects. *The Quarterly Journal of Economics, 133*(3), 1107–1162.
https://doi.org/10.1093/qje/qjy007

Chetty, R., Hendren, N., & Katz, L. F. (2016). The effects of exposure to better neighborhoods on
children: New evidence from the Moving to Opportunity experiment. *American Economic Review,
106*(4), 855–902. https://doi.org/10.1257/aer.20150572

Durlauf, S. N., Kourtellos, A., & Tan, C. M. (2022). The Great Gatsby curve. *Annual Review of
Economics, 14*, 571–605. https://doi.org/10.1146/annurev-economics-082321-122703

Feinberg, R. M., & Kuehn, D. (2020). Does a guaranteed basic income encourage entrepreneurship?
Evidence from Alaska. *Review of Industrial Organization, 57*(3), 607–626.
https://doi.org/10.1007/s11151-020-09786-8

Glavan, S. (2024). Baby bonds: Saving for America's future. *Policy Perspectives, 31*.
https://doi.org/10.4079/pp.v31i0.4

Greenaway-McGrevy, R. (2025). Evaluating the long-run effects of zoning reform on urban
development. *Regional Science and Urban Economics, 111*, Article 104062.
https://doi.org/10.1016/j.regsciurbeco.2024.104062

Gyourko, J., & Krimmel, J. (2021). The impact of local residential land use restrictions on land
values across and within single family housing markets. *Journal of Urban Economics, 126*,
Article 103374. https://doi.org/10.1016/j.jue.2021.103374

Huang, J., Sherraden, M., Clancy, M. M., Beverly, S. G., Shanks, T. R., & Kim, Y. (2021). Asset
building and child development: A policy model for inclusive child development accounts. *RSF:
The Russell Sage Foundation Journal of the Social Sciences, 7*(3), 176–195.
https://doi.org/10.7758/rsf.2021.7.3.08

Hughes, C., Sayce, S., Shepherd, E., & Wyatt, P. (2020). Implementing a land value tax:
Considerations on moving from theory to practice. *Land Use Policy, 94*, Article 104494.
https://doi.org/10.1016/j.landusepol.2020.104494

Iacono, R., & Palagi, E. (2023). A micro perspective on r > g. *Economica, 90*(358), 531–556.
https://doi.org/10.1111/ecca.12464

Iacono, R., & Smedsvik, B. (2026). Behavioural responses to wealth taxation: Evidence from a
Norwegian reform. *Fiscal Studies, 47*(3), 255–280. https://doi.org/10.1111/1475-5890.70024

Jakurti, E. (2025). A tale of two rates: Return on capital, economic growth, and wealth
concentration in the long run. *Review of Political Economy, 38*(3), 927–960.
https://doi.org/10.1080/09538259.2025.2492268

Jerrim, J., & Macmillan, L. (2015). Income inequality, intergenerational mobility, and the Great
Gatsby curve: Is education the key? *Social Forces, 94*(2), 505–533.
https://doi.org/10.1093/sf/sov075

Jones, D., & Marinescu, I. (2022). The labor market impacts of universal and permanent cash
transfers: Evidence from the Alaska Permanent Fund. *American Economic Journal: Economic Policy,
14*(2), 315–340. https://doi.org/10.1257/pol.20190299

Kleiner, M. M., Marier, A., Park, K. W., & Wing, C. (2016). Relaxing occupational licensing
requirements: Analyzing wages and prices for a medical service. *The Journal of Law and
Economics, 59*(2), 261–291. https://doi.org/10.1086/688093

Kleiner, M. M., & Soltas, E. J. (2023). A welfare analysis of occupational licensing in U.S.
states. *The Review of Economic Studies, 90*(5), 2481–2516. https://doi.org/10.1093/restud/rdad015

Londoño-Vélez, J., & Ávila-Mahecha, J. (2024). *Behavioral responses to wealth taxation: Evidence
from Colombia* (NBER Working Paper No. 32134). National Bureau of Economic Research.
https://doi.org/10.3386/w32134

Ludwig, J., Duncan, G. J., Gennetian, L. A., Katz, L. F., Kessler, R. C., Kling, J. R., &
Sanbonmatsu, L. (2013). Long-term neighborhood effects on low-income families: Evidence from
Moving to Opportunity. *American Economic Review, 103*(3), 226–231.
https://doi.org/10.1257/aer.103.3.226

Mas-Montserrat, M., Durán-Cabré, J. M., & Esteller-Moré, A. (2025). Avoidance responses to the
wealth tax. *Journal of Public Economics, 246*, Article 105351.
https://doi.org/10.1016/j.jpubeco.2025.105351

Murphy, D., & Seegert, N. (2026). Implicit land taxes and their effect on the real economy.
*Journal of Public Economics, 261*, Article 105735. https://doi.org/10.1016/j.jpubeco.2026.105735

Piketty, T. (2015). Putting distribution back at the center of economics: Reflections on
*Capital in the Twenty-First Century*. *Journal of Economic Perspectives, 29*(1), 67–88.
https://doi.org/10.1257/jep.29.1.67

Quigley, J. M., & Rosenthal, L. A. (2005). The effects of land-use regulation on the price of
housing: What do we know? What can we learn? *Cityscape, 8*(1), 69–137.
https://consensus.app/papers/details/9155b87715b459bf9f9359bfb57e4c42/

Redbird, B. (2017). The new closed shop? The economic and structural effects of occupational
licensure. *American Sociological Review, 82*(3), 600–624.
https://doi.org/10.1177/0003122417706463

Seim, D. (2017). Behavioral responses to wealth taxes: Evidence from Sweden. *American Economic
Journal: Economic Policy, 9*(4), 395–421. https://doi.org/10.1257/pol.20150290

Skaburskis, A. (1995). The consequence of taxing land value. *Journal of Planning Literature,
10*(1), 3–21. https://doi.org/10.1177/088541229501000101

Stacy, C., Davis, C., Freemark, Y. S., Lo, L., MacDonald, G., Zheng, V., & Pendall, R. (2023).
Land-use reforms and housing costs: Does allowing for increased density lead to greater
affordability? *Urban Studies, 60*(14), 2919–2940. https://doi.org/10.1177/00420980231159500

Strauss, D., & Ventosa-Santaularia, D. (2023). Does r − g cause wealth inequality? The case of
the United States. *Estudios Económicos de El Colegio de México, 38*(2), 183–224.
https://doi.org/10.24201/ee.v38i2.441

Sun, Y., Caccioli, F., Li, X., & Livan, G. (2024). The academic Great Gatsby curve. *Journal of
the Royal Society Interface, 21*(217), Article 20240173. https://doi.org/10.1098/rsif.2024.0173

Wenner, F. (2018). Sustainable urban development and land value taxation: The case of Estonia.
*Land Use Policy, 77*, 790–800. https://doi.org/10.1016/j.landusepol.2016.08.031

Zewde, N. (2019). Universal baby bonds reduce Black-White wealth inequality, progressively raise
net worth of all young adults. *The Review of Black Political Economy, 47*(1), 3–19.
https://doi.org/10.1177/0034644619885321
