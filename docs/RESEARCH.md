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
- [M59: respectful play](#m59-respectful-play) (searched 2026-10-23)

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

## M59: respectful play

Evidence for [M59](ROADMAP.md#m59-respectful-play-6-h) (first drafted as "M60"). Its aim:
players feel rewarded, but never feel they must give up work, family or friends to keep up. M59
runs the bot league with players on different schedules (a weekend player, a shift worker, a
parent with 30 minutes a day, a daily grinder) and fails the economy check (M23) when a change
makes absence costlier or rewards streaks, short windows or fixed appointments.

The question for the research: what actually harms players, and which design levers help?

### What the evidence changes in the design

1. **Hours played are the wrong target.** Studies that link players' well-being to logged play
   data find little or no effect of time played (Vuorre et al., 2022; Ballou et al., 2024;
   Ballou et al., 2025; Larrieu et al., 2023), a small positive one (Johannes et al., 2021), or a
   positive causal effect (Egami et al., 2024). Hard caps on time also have a weak record
   (Zendle et al., 2023). So the check should **not** cap or penalise hours. It should measure
   the pressure to play.
2. **The harm is "having to" rather than "wanting to".** Obsessive passion, the feeling that play
   is compelled, goes with tension, low enjoyment and lower well-being; harmonious passion does
   not (Przybylski et al., 2009). Obsessive passion is predicted by unmet needs in the rest of
   life (Johnson et al., 2022), and players experience daily engagement rewards both as motivation
   and as an obligation or chore that feeds fear of missing out (Frommel & Mandryk, 2022). The
   measures that matter are the ones that create obligation: cost of absence, streaks,
   appointments and short windows.
3. **Social play is good, social obligation is not.** Playing with others builds social capital
   through harmonious passion (Perry et al., 2018), and harmonious passion in World of Warcraft
   reduces loneliness (Mandryk et al., 2020). But among MMORPG players, the effect of social
   identity on game addiction runs through fear of missing out (Duman & Ozkara, 2019). Group
   content should therefore be asynchronous, and no group should be penalised for one member's
   absence.
4. **Known rewards, not random ones.** Paying for loot boxes is consistently linked to problem
   gambling (Garea et al., 2021; Spicer et al., 2021; Zendle et al., 2020), including in
   adolescents after controlling for gambling (Hing et al., 2022), and reward variability is a
   proposed route to addictive potential (Clark & Zack, 2023). Questless contracts already escrow
   a fixed, visible reward before they exist; the check should keep it that way and flag any
   random reward schedule tied to play time or spending.

### Findings by lever

#### Time played and well-being

| Finding | Design consequence |
|---|---|
| Linking well-being surveys to play logs from Electronic Arts and Nintendo, play time had a small positive relation with affective well-being (Johannes et al., 2021). | Don't treat playing more as a harm in itself. |
| Six weeks of logged play from 38,935 players across seven publishers showed little to no evidence of a causal link between play time and well-being; motivations mattered (Vuorre et al., 2022). | Measure motivation-related pressures, not hours. |
| A preregistered 12-week Xbox panel found no practically significant link between logged play time and well-being in either direction (Ballou et al., 2024). | Same. |
| Across 150 Nintendo Switch games, hours did not predict well-being, but how well gaming fits into players' lives ("gaming life fit") did (Ballou et al., 2025). | The target is how play fits a life, which is what schedule fairness and safe stopping measure. |
| Winning a console lottery in Japan, and the extra play it brought, improved mental well-being (Egami et al., 2024). | Play can help; the goal is not less play. |
| Among intensive gamers, logged play time was not related to quality of life; gaming-disorder symptoms and quality of life shared risk factors such as impulsivity (Larrieu et al., 2023). | Intensive play is not in itself a problem; avoid designs that target vulnerable players. |
| Evening gaming helped employees recover from work through detachment and mastery, more so with harmonious passion (Koçak et al., 2023). | Short, evening-sized sessions with a natural end support the "real life first" goal. |

#### Obligation and passion

| Finding | Design consequence |
|---|---|
| Low need satisfaction goes with obsessive passion, more play, tension after play and low enjoyment; high play hurt well-being only for obsessively passionate players (Przybylski et al., 2009). | Measure what makes play feel compulsory. |
| Obsessive passion is predicted by low need satisfaction in general life, not just in the game (Johnson et al., 2022). | The game can't fix life, but it must not exploit those gaps: no penalties for being away. |
| Self-regulation explains the link between passion and well-being better than play time (Luxford et al., 2022). | Offer tools that support self-regulation: player-set goals and an optional, judgement-free play summary. |

#### Engagement rewards, streaks and appointments

| Finding | Design consequence |
|---|---|
| Players experience daily login rewards and repeatable challenges as motivation, as fear of missing out, or as an obligation or chore (Frommel & Mandryk, 2022). | Streak dependence and daily-only rewards are measured and capped near zero. |
| An ethnography of World of Warcraft shows how design features and community norms together produce routines and expectations about when to play (Rapp, 2021). | Check both the mechanics and the norms they create, for example raid times. |
| "Playing by appointment", forcing play at specific times through rewards or punishments, and grinding are among the most common dark patterns in profitable casual games (Dahlan & Susanty, 2022). | Fixed-time events need a catch-up path; grinding gets diminishing returns. |
| Across 1,496 games, dark patterns appear even in games seen as healthy (Niknejad et al., 2024). | Every change is checked, not only the obviously monetised ones. |
| Players reported 35 unfair or aggressive monetisation techniques in eight domains, several of which fall outside UK consumer law (Petrovskaya & Zendle, 2021). | Use the list as a checklist for the proposed regulator and researcher view. |

#### Fear of missing out and social pressure

| Finding | Design consequence |
|---|---|
| Among 318 MMORPG players, the effect of social identity on game addiction was fully mediated by fear of missing out, more strongly for those with a high need to belong (Duman & Ozkara, 2019). | Guild and group mechanics must not turn belonging into attendance pressure. |
| A systematic review of 13 studies confirms a correlation, and a direct effect, of fear of missing out on gaming disorder (Caba-Machado et al., 2024). | Count offers that last under a week or have no catch-up path, and fail the check above a threshold. |
| Playing with friends and strangers builds social capital through harmonious passion (Perry et al., 2018); harmonious passion in World of Warcraft reduced loneliness while obsessive passion increased it (Mandryk et al., 2020). | Keep social play, remove the obligation: asynchronous group contracts with flexible windows. |

#### Paid randomness

| Finding | Design consequence |
|---|---|
| Meta-analysis: loot box spending correlates with problem gambling (r = 0.26) and excessive gaming (r = 0.25) (Garea et al., 2021). | No paid random rewards, ever. |
| Systematic review: 12 of 13 publications found a positive loot box–problem gambling link (mean r = .27) (Spicer et al., 2021). | Same. |
| The link holds whatever the loot box's features, if it is sold for real money (Zendle et al., 2020). | Don't try to design a "safe" loot box. |
| In adolescents, recent loot box purchasing raised the odds of problem gambling 3.7 to 6.0 times after controlling for gambling (Hing et al., 2022). | Same, especially for young players. |
| Reward variability and frequency may give non-drug rewards addictive potential (Clark & Zack, 2023). | Keep contract rewards fixed and known in advance (they are escrowed); keep randomness in world events, not reward schedules. |

#### Hard limits imposed from outside

| Finding | Design consequence |
|---|---|
| Telemetry covering over seven billion hours found no credible reduction in heavy play after China's 2019 playtime limits for minors (Zendle et al., 2023). | Don't rely on hard caps. |
| After the 2021 limits, a minority of heavy adolescent gamers got around them with other people's accounts, and 59% shifted to watching short videos (Zhou et al., 2024). | Caps can move the time elsewhere; design for less pressure instead. |
| The same restrictions did reduce underage spending, including on loot boxes (Xiao, 2022). | Spending protections can work even where time limits don't. |

### What the evidence does not settle

- Most loot-box and fear-of-missing-out studies are cross-sectional, so the direction of cause is
  unclear (Spicer et al., 2021; Caba-Machado et al., 2024).
- Evidence on China's limits conflicts: industry telemetry shows no reduction in heavy play
  (Zendle et al., 2023), while a survey after the 2021 rules found most heavy adolescent gamers
  complying (Zhou et al., 2024).
- Studies of play time and well-being mostly cover adults and single platforms; equivalence tests
  were sometimes inconclusive (Ballou et al., 2025).

### Gaps not yet searched

- Notifications and interruptions, and their effect on stress outside play.
- Catch-up mechanics such as rested bonuses, and whether they reduce pressure.
- Children's design codes (for example the UK Age Appropriate Design Code) and consumer law on
  dark patterns.
- How guild and raid scheduling norms form, beyond a single ethnography.

### References

Ballou, N., Sewall, C. J. R., Ratcliffe, J., Zendle, D., Tokarchuk, L., & Deterding, S. (2024).
Registered report evidence suggests no relationship between objectively tracked video game
playtime and well-being over 3 months. *Technology, Mind, and Behavior, 5*(1), 28–42.
https://doi.org/10.1037/tmb0000124

Ballou, N., Vuorre, M., Hakman, T., Magnusson, K., & Przybylski, A. K. (2025). Perceived value of
video games, but not hours played, predicts mental well-being in casual adult Nintendo players.
*Royal Society Open Science, 12*(3), Article 241174. https://doi.org/10.1098/rsos.241174

Caba-Machado, V., Díaz-López, A., Machimbarrena, J. M., & González-Cabrera, J. (2024). Fear of
missing out, gaming disorder and internet gaming disorder: Systematic review. *Current Addiction
Reports, 11*(6), 1006–1015. https://doi.org/10.1007/s40429-024-00595-7

Clark, L., & Zack, M. (2023). Engineered highs: Reward variability and frequency as potential
prerequisites of behavioural addiction. *Addictive Behaviors, 140*, Article 107626.
https://doi.org/10.1016/j.addbeh.2023.107626

Dahlan, R. P., & Susanty, M. (2022). Finding dark patterns in casual mobile games using heuristic
evaluation. *PETIR, 15*(2), 185–195. https://doi.org/10.33322/petir.v15i2.1151

Duman, H., & Ozkara, B. Y. (2019). The impact of social identity on online game addiction: The
mediating role of the fear of missing out (FoMO) and the moderating role of the need to belong.
*Current Psychology, 40*(9), 4571–4580. https://doi.org/10.1007/s12144-019-00392-w

Egami, H., Rahman, M. S., Yamamoto, T., Egami, C., & Wakabayashi, T. (2024). Causal effect of
video gaming on mental well-being in Japan 2020–2022. *Nature Human Behaviour, 8*(10),
1943–1956. https://doi.org/10.1038/s41562-024-01948-y

Frommel, J., & Mandryk, R. L. (2022). Daily quests or daily pests? The benefits and pitfalls of
engagement rewards in games. *Proceedings of the ACM on Human-Computer Interaction, 6*(CHI PLAY),
1–23. https://doi.org/10.1145/3549489

Garea, S. S., Drummond, A., Sauer, J. D., Hall, L. C., & Williams, M. N. (2021). Meta-analysis of
the relationship between problem gambling, excessive gaming and loot box spending.
*International Gambling Studies, 21*(3), 460–479. https://doi.org/10.1080/14459795.2021.1914705

Hing, N., Rockloff, M., Russell, A. M. T., Browne, M., Newall, P., Greer, N., King, D. L., &
Thorne, H. (2022). Loot box purchasing is linked to problem gambling in adolescents when
controlling for monetary gambling participation. *Journal of Behavioral Addictions*.
https://doi.org/10.1556/2006.2022.00015

Johannes, N., Vuorre, M., & Przybylski, A. K. (2021). Video game play is positively correlated
with well-being. *Royal Society Open Science, 8*(2), Article 202049.
https://doi.org/10.1098/rsos.202049

Johnson, D., Formosa, J., Perry, R., Lalande, D., Türkay, S., Obst, P., & Mandryk, R. (2022).
Unsatisfied needs as a predictor of obsessive passion for videogame play. *Psychology of Popular
Media, 11*(1), 47–55. https://doi.org/10.1037/ppm0000299

Koçak, Ö. E., Gorgievski, M., & Bakker, A. B. (2023). Recovery from work by playing video games.
*Applied Psychology, 73*(3), 1331–1360. https://doi.org/10.1111/apps.12519

Larrieu, M., Fombouchet, Y., Billieux, J., & Decamps, G. (2023). How gaming motives affect the
reciprocal relationships between video game use and quality of life: A prospective study using
objective playtime indicators. *Computers in Human Behavior, 147*, Article 107824.
https://doi.org/10.1016/j.chb.2023.107824

Luxford, E., Türkay, S., Frommel, J., Tobin, S. J., Mandryk, R. L., Formosa, J., & Johnson, D.
(2022). Self-regulation as a mediator of the associations between passion for video games and
well-being. *Cyberpsychology, Behavior, and Social Networking, 25*(5), 310–315.
https://doi.org/10.1089/cyber.2021.0321

Mandryk, R. L., Frommel, J., Armstrong, A., & Johnson, D. (2020). How passion for playing World
of Warcraft predicts in-game social capital, loneliness, and wellbeing. *Frontiers in Psychology,
11*, Article 2165. https://doi.org/10.3389/fpsyg.2020.02165

Niknejad, S., Mildner, T., Zargham, N., Putze, S., & Malaka, R. (2024). Level up or game over:
Exploring how dark patterns shape mobile games. In *Proceedings of the International Conference
on Mobile and Ubiquitous Multimedia* (pp. 148–156). https://doi.org/10.1145/3701571.3701604

Perry, R., Drachen, A., Kearney, A., Kriglstein, S., Nacke, L. E., Sifa, R., Wallner, G., &
Johnson, D. (2018). Online-only friends, real-life friends or strangers? Differential
associations with passion and social capital in video game play. *Computers in Human Behavior,
79*, 202–210. https://doi.org/10.1016/j.chb.2017.10.032

Petrovskaya, E., & Zendle, D. (2021). Predatory monetisation? A categorisation of unfair,
misleading and aggressive monetisation techniques in digital games from the player perspective.
*Journal of Business Ethics, 181*(4), 1065–1081. https://doi.org/10.1007/s10551-021-04970-6

Przybylski, A. K., Weinstein, N., Ryan, R. M., & Rigby, C. S. (2009). Having to versus wanting to
play: Background and consequences of harmonious versus obsessive engagement in video games.
*CyberPsychology & Behavior, 12*(5), 485–492. https://doi.org/10.1089/cpb.2009.0083

Rapp, A. (2021). Time, engagement and video games: How game design elements shape the
temporalities of play in massively multiplayer online role-playing games. *Information Systems
Journal, 32*(1), 5–32. https://doi.org/10.1111/isj.12328

Spicer, S. G., Nicklin, L. L., Uther, M., Lloyd, J., Lloyd, H., & Close, J. (2021). Loot boxes,
problem gambling and problem video gaming: A systematic review and meta-synthesis. *New Media &
Society, 24*(4), 1001–1022. https://doi.org/10.1177/14614448211027175

Vuorre, M., Johannes, N., Magnusson, K., & Przybylski, A. K. (2022). Time spent playing video
games is unlikely to impact well-being. *Royal Society Open Science, 9*(7), Article 220411.
https://doi.org/10.1098/rsos.220411

Xiao, L. Y. (2022). Reserve your judgment on "Draconian" Chinese video gaming restrictions on
children. *Journal of Behavioral Addictions*. https://doi.org/10.1556/2006.2022.00022

Zendle, D., Cairns, P., Barnett, H., & McCall, C. (2020). Paying for loot boxes is linked to
problem gambling, regardless of specific features like cash-out and pay-to-win. *Computers in
Human Behavior, 102*, 181–191. https://doi.org/10.1016/j.chb.2019.07.003

Zendle, D., Flick, C., Gordon-Petrovskaya, E., Ballou, N., Xiao, L. Y., & Drachen, A. (2023). No
evidence that Chinese playtime mandates reduced heavy gaming in one segment of the video games
industry. *Nature Human Behaviour, 7*(10), 1753–1766. https://doi.org/10.1038/s41562-023-01669-8

Zhou, X., Liao, M., Gorowska, M., Chen, X., & Li, Y. (2024). Compliance and alternative behaviors
of heavy gamers in adolescents to Chinese online gaming restriction policy. *Journal of
Behavioral Addictions, 13*(2), 687–692. https://doi.org/10.1556/2006.2024.00021
