<?xml version="1.0" ?><StyledLayerDescriptor version="1.0.0" xmlns="http://www.opengis.net/sld" xmlns:ogc="http://www.opengis.net/ogc" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">
  <NamedLayer>
    <Name>s0127_rijnland_kwetsbare_objecten</Name>
    <UserStyle>
      <Title>s0127_rijnland_kwetsbare_objecten</Title>
      <FeatureTypeStyle>
        <Rule>
         <MaxScaleDenominator>30000</MaxScaleDenominator>
          <PointSymbolizer>
            <Graphic>
              <ExternalGraphic>
                <OnlineResource xlink:href="https://media.klimaatatlas.net/klimaatatlas/iconen-algemeen/kwetsbare-objecten/${image}" xlink:type="simple"/>
                <Format>image/svg+xml</Format>
              </ExternalGraphic>
              <Size>20</Size>
            </Graphic>
          </PointSymbolizer>
        </Rule>
        <Rule>
          <MinScaleDenominator>30000</MinScaleDenominator>
    	  <MaxScaleDenominator>250000</MaxScaleDenominator>
          <PointSymbolizer>
            <Graphic>
              <ExternalGraphic>
                <OnlineResource xlink:href="https://media.klimaatatlas.net/klimaatatlas/iconen-algemeen/kwetsbare-objecten/${image}" xlink:type="simple"/>
                <Format>image/svg+xml</Format>
              </ExternalGraphic>
              <Size>12</Size>
            </Graphic>
          </PointSymbolizer>
        </Rule>
        <Rule>
          <MinScaleDenominator>250000</MinScaleDenominator>
    	  <MaxScaleDenominator>500000</MaxScaleDenominator>
          <PointSymbolizer>
            <Graphic>
              <ExternalGraphic>
                <OnlineResource xlink:href="https://media.klimaatatlas.net/klimaatatlas/iconen-algemeen/kwetsbare-objecten/${image}" xlink:type="simple"/>
                <Format>image/svg+xml</Format>
              </ExternalGraphic>
              <Size>6</Size>
            </Graphic>
          </PointSymbolizer>
        </Rule>
        <Rule>
          <MinScaleDenominator>500000</MinScaleDenominator>
    	  <MaxScaleDenominator>800000</MaxScaleDenominator>
          <PointSymbolizer>
            <Graphic>
              <ExternalGraphic>
                <OnlineResource xlink:href="https://media.klimaatatlas.net/klimaatatlas/iconen-algemeen/kwetsbare-objecten/${image}" xlink:type="simple"/>
                <Format>image/svg+xml</Format>
              </ExternalGraphic>
              <Size>3</Size>
            </Graphic>
          </PointSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>